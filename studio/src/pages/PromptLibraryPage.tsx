import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface PromptPart {
  id: string;
  name: string;
  description: string;
  content: string;
  category: string;
  tags: string[];
  version: string;
  updatedAt: string;
}

const mockParts: PromptPart[] = [
  {
    id: '1',
    name: 'Helpful Assistant',
    description: "A generic but friendly assistant persona that's helpful and concise in its responses.",
    content: 'You are a helpful assistant...',
    category: 'System Roles',
    tags: ['persona', 'analysis'],
    version: '1.0.1',
    updatedAt: '2 days ago',
  },
  {
    id: '2',
    name: 'JSON Output',
    description: 'Forces the model to output a valid JSON object matching a specified schema.',
    content: 'Output your response as valid JSON...',
    category: 'Formatting',
    tags: ['json', 'summarization'],
    version: '2.1.0',
    updatedAt: '1 week ago',
  },
  {
    id: '3',
    name: 'Code Snippet Injector',
    description: 'Provides context by injecting a file or code snippet into the prompt.',
    content: 'Here is the relevant code context...',
    category: 'Context Injection',
    tags: [],
    version: '1.0.0',
    updatedAt: '3 weeks ago',
  },
  {
    id: '4',
    name: 'Summarize Key Points',
    description: 'Instructs the model to provide a brief summary highlighting the key takeaways from a text.',
    content: 'Please summarize the key points...',
    category: 'Output Instructions',
    tags: [],
    version: '1.2.0',
    updatedAt: '1 month ago',
  },
];

const categories = [
  { name: 'System Roles', count: 5 },
  { name: 'Formatting', count: 8 },
  { name: 'Context Injection', count: 3 },
  { name: 'Output Instructions', count: 12 },
  { name: 'Utilities', count: 2 },
];

const tags = ['json', 'summarization', 'persona', 'analysis'];

export function PromptLibraryPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const filteredParts = useMemo(() => {
    return mockParts.filter(part => {
      const matchesCategory = !selectedCategory || part.category === selectedCategory;

      const matchesTags = selectedTags.length === 0 ||
        selectedTags.every(tag => part.tags.includes(tag));

      const matchesSearch = !search ||
        part.name.toLowerCase().includes(search.toLowerCase()) ||
        part.tags.some(tag => tag.toLowerCase().includes(search.toLowerCase()));

      return matchesCategory && matchesTags && matchesSearch;
    });
  }, [search, selectedCategory, selectedTags]);

  const toggleTag = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  };

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
            {tags.map(tag => (
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
            <Button onClick={() => navigate('/library/new')}>
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
                  onClick={() => navigate(`/library/part?id=${part.id}`)}
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
                      Updated {part.updatedAt}
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
