import { useState } from 'react';
import { Search, ChevronRight, ChevronDown, Trash2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { usePromptParts } from '@/hooks/useApi';
import type { PromptPart } from '@/types';

interface PromptPartsPanelProps {
  projectId: string | undefined;
  onInsertPart: (category: string, partId: string) => void;
  usedParts?: Array<{ category: string; partId: string }>;
  onDeletePart?: (category: string, partId: string) => void;
}

export function PromptPartsPanel({
  projectId,
  onInsertPart,
  usedParts = [],
  onDeletePart
}: PromptPartsPanelProps) {
  const { parts, loading, error } = usePromptParts(projectId);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  const filterParts = (partsList: PromptPart[]): PromptPart[] => {
    if (!searchQuery.trim()) return partsList;

    const query = searchQuery.toLowerCase();
    return partsList.filter(part =>
      part.name.toLowerCase().includes(query) ||
      part.part_id.toLowerCase().includes(query) ||
      part.description?.toLowerCase().includes(query) ||
      part.tags.some(tag => tag.toLowerCase().includes(query))
    );
  };

  const isPartUsed = (category: string, partId: string): boolean => {
    return usedParts.some(p => p.category === category && p.partId === partId);
  };

  if (loading) {
    return (
      <div className="p-4">
        <p className="text-sm text-muted-foreground">Loading parts...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    );
  }

  if (!parts || Object.keys(parts.by_category).length === 0) {
    return (
      <div className="p-4">
        <p className="text-sm text-muted-foreground">No prompt parts available</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 space-y-3 border-b border-border">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">Prompt Parts</h3>
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
        </div>

        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search parts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 pl-8 text-sm"
          />
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {Object.entries(parts.by_category).map(([category, categoryParts]) => {
          const filteredParts = filterParts(categoryParts);
          if (filteredParts.length === 0) return null;

          const isExpanded = expandedCategories.has(category);

          return (
            <div key={category} className="border-b border-border">
              <button
                onClick={() => toggleCategory(category)}
                className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {isExpanded ? (
                    <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
                  )}
                  <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    {category}
                  </span>
                </div>
                <Badge variant="secondary" className="text-xs">
                  {filteredParts.length}
                </Badge>
              </button>

              {isExpanded && (
                <div className="pb-2">
                  {filteredParts.map((part) => {
                    const used = isPartUsed(category, part.part_id);

                    return (
                      <div
                        key={part.id}
                        className="group px-4 py-2 hover:bg-accent/30 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <button
                            onClick={() => onInsertPart(category, part.part_id)}
                            className="flex-1 text-left"
                            disabled={used}
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium">
                                {part.name}
                              </span>
                              {used && (
                                <Badge variant="outline" className="text-xs">
                                  In use
                                </Badge>
                              )}
                            </div>
                            {part.description && (
                              <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                                {part.description}
                              </p>
                            )}
                            {part.tags.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1.5">
                                {part.tags.map((tag) => (
                                  <Badge
                                    key={tag}
                                    variant="secondary"
                                    className="text-xs px-1.5 py-0"
                                  >
                                    {tag}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </button>

                          {used && onDeletePart && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => onDeletePart(category, part.part_id)}
                              className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              <Trash2 className="w-3.5 h-3.5 text-destructive" />
                            </Button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}