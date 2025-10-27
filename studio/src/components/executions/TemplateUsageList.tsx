import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { TemplateUsageEntry } from '@/types';
import { ChevronDown, ExternalLink, FileCode, Copy, Check, Eye } from 'lucide-react';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

interface TemplateUsageListProps {
  templateUsages: TemplateUsageEntry[];
}

export function TemplateUsageList({ templateUsages }: TemplateUsageListProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const navigate = useNavigate();
  const { projectSlug } = useParams<{ projectSlug?: string }>();
  const resolvedProjectSlug = projectSlug ?? 'default';

  const handleOpenTemplate = (promptId: string) => {
    navigate(`/project/${resolvedProjectSlug}/prompt/edit?prompt=${encodeURIComponent(promptId)}`);
  };

  const handleCopy = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1500);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  if (templateUsages.length === 0) {
    return null;
  }

  const sortedUsages = templateUsages.slice().sort((a, b) => a.position - b.position);

  return (
    <Card className="p-5 border-indigo-200 bg-gradient-to-br from-indigo-50/50 to-purple-50/30">
      <div className="flex items-start justify-between mb-4 pb-4 border-b border-indigo-200">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-indigo-600 rounded-lg">
            <FileCode className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-indigo-900">Templates Used</h2>
            <p className="text-xs text-indigo-700">
              {templateUsages.length} template{templateUsages.length === 1 ? '' : 's'} linked to this execution
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {sortedUsages.map((usage, index) => {
            const isExpanded = expandedIndex === index;
            const isCopied = copiedIndex === index;

            return (
              <div
                key={`${usage.promptId}-${usage.version}-${usage.position}`}
                className="border border-indigo-200 bg-white rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                {/* Header */}
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="outline" className="bg-indigo-100 text-indigo-700 border-indigo-300 font-mono text-xs">
                        #{usage.position + 1}
                      </Badge>
                      <button
                        onClick={() => handleOpenTemplate(usage.promptId)}
                        className="text-sm font-semibold text-indigo-600 hover:text-indigo-700 hover:underline inline-flex items-center gap-1.5 group"
                      >
                        <FileCode className="w-4 h-4" />
                        {usage.promptId}
                        <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </button>
                      <Badge variant="secondary" className="text-xs font-mono">
                        v{usage.version}
                      </Badge>
                    </div>
                  </div>
                </div>

                {/* Inputs */}
                {usage.inputs && Object.keys(usage.inputs).length > 0 && (
                  <div className="mb-3">
                    <div className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wide">
                      Template Inputs
                    </div>
                    <div className="space-y-1.5">
                      {Object.entries(usage.inputs).map(([key, value]) => (
                        <div
                          key={key}
                          className="flex items-start gap-2 text-xs bg-muted/50 px-3 py-2 rounded border border-border/60"
                        >
                          <code className="font-semibold text-indigo-700 flex-shrink-0">{key}:</code>
                          <code className="text-foreground break-all flex-1">
                            {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                          </code>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Rendered Prompt Toggle */}
                {usage.renderedPrompt && (
                  <div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setExpandedIndex(isExpanded ? null : index)}
                      className="w-full justify-between h-8 text-xs font-medium hover:bg-indigo-100/50"
                    >
                      <span className="flex items-center gap-2">
                        <Eye className="w-3.5 h-3.5" />
                        {isExpanded ? 'Hide' : 'View'} Rendered Prompt
                      </span>
                      <ChevronDown
                        className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      />
                    </Button>

                    {isExpanded && (
                      <div className="mt-3 relative">
                        <div className="absolute top-2 right-2 z-10">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 bg-white/90 hover:bg-white"
                            onClick={() => handleCopy(usage.renderedPrompt!, index)}
                          >
                            {isCopied ? (
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="w-3.5 h-3.5 text-muted-foreground" />
                            )}
                          </Button>
                        </div>
                        <pre className="rounded-md bg-slate-950 border border-slate-800 p-4 text-xs text-slate-200 overflow-x-auto font-mono leading-relaxed max-h-96 overflow-y-auto">
                          {usage.renderedPrompt}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
      </div>
    </Card>
  );
}
