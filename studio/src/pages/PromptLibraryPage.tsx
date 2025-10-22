import { useState, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import { usePromptParts } from '@/hooks/useApi';

export function PromptLibraryPage() {
  const navigate = useNavigate();
  const { projectSlug } = useParams<{ projectSlug: string }>();
  const { projectId, contextLoading } = useAuthenticatedApi();
  const { parts, loading, error } = usePromptParts(projectId);

  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  // Flatten all parts from categories
  const allParts = useMemo(() => {
    if (!parts?.by_category) return [];
    return Object.values(parts.by_category).flat();
  }, [parts]);

  // Extract categories with counts
  const categories = useMemo(() => {
    if (!parts?.by_category) return [];
    return Object.entries(parts.by_category).map(([name, items]) => ({
      name,
      count: items.length,
    }));
  }, [parts]);

  // Extract all unique tags
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    allParts.forEach(part => {
      part.tags.forEach(tag => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }, [allParts]);

  const filteredParts = useMemo(() => {
    return allParts.filter(part => {
      const matchesCategory = !selectedCategory || part.category === selectedCategory;

      const matchesTags = selectedTags.length === 0 ||
        selectedTags.every(tag => part.tags.includes(tag));

      const matchesSearch = !search ||
        part.name.toLowerCase().includes(search.toLowerCase()) ||
        part.tags.some(tag => tag.toLowerCase().includes(search.toLowerCase()));

      return matchesCategory && matchesTags && matchesSearch;
    });
  }, [allParts, search, selectedCategory, selectedTags]);

  const toggleTag = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  };

  if (contextLoading || loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">Loading prompt parts...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-destructive">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="h-full flex">
      <div className="w-64 border-r border-border bg-card flex flex-col">
        <div className="p-4 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground mb-3">Categories</h2>
          <div className="space-y-1">
            {categories.map(category => (
              <button
                key={category.name}
                onClick={() => setSelectedCategory(
                  selectedCategory === category.name ? null : category.name
                )}
                className={cn(
                  "w-full flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors",
                  selectedCategory === category.name
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                )}
              >
                <span>{category.name}</span>
                <span className="text-xs">{category.count}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="p-4">
          <h2 className="text-sm font-semibold text-foreground mb-3">Tags</h2>
          <div className="flex flex-wrap gap-2">
            {allTags.map(tag => (
              <Badge
                key={tag}
                variant={selectedTags.includes(tag) ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => toggleTag(tag)}
              >
                {tag}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        <div className="border-b border-border bg-card px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-semibold">Prompt Snippet Library</h1>
            <Button onClick={() => navigate(`/project/${projectSlug}/library/new`)}>
              + New Part
            </Button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search all snippets..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
            <kbd className="absolute right-3 top-1/2 transform -translate-y-1/2 pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border border-border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
              ⌘K
            </kbd>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {filteredParts.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              {search || selectedCategory || selectedTags.length > 0
                ? 'No snippets found matching your filters'
                : 'No snippets yet'}
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {filteredParts.map(part => (
                <Card
                  key={part.id}
                  className="p-4 hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => navigate(`/project/${projectSlug}/library/part?id=${part.part_id}`)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge
                          variant="secondary"
                          className="text-xs font-normal"
                        >
                          {part.category}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {part.version}
                        </Badge>
                      </div>
                      <h3 className="font-semibold text-base">{part.name}</h3>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                    {part.description}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      Updated {part.updated_at}
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
