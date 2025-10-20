import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Plus, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import type { Template } from '@/types';

export function DashboardPage() {
  const navigate = useNavigate();
  const { api } = useAuthenticatedApi();
  const [prompts, setPrompts] = useState<Template[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadPrompts = async () => {
      try {
        const promptIds = await api.getPrompts();
        const promptData = await Promise.all(
          promptIds.map(id => api.getPrompt(id))
        );
        setPrompts(promptData);
      } catch (error) {
        console.error('Failed to load prompts:', error);
      } finally {
        setLoading(false);
      }
    };

    loadPrompts();
  }, [api]);

  const filteredPrompts = prompts.filter(t =>
    t.id.toLowerCase().includes(search.toLowerCase()) ||
    t.description?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-semibold">Prompts</h1>
          <Button onClick={() => navigate('/prompts/new')}>
            <Plus className="w-4 h-4 mr-2" />
            New Prompt
          </Button>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search prompts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {loading ? (
          <div className="text-center py-12 text-muted-foreground">Loading prompts...</div>
        ) : filteredPrompts.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            {search ? 'No prompts found' : 'No prompts yet'}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredPrompts.map(prompt => (
              <Card
                key={prompt.id}
                className="p-4 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => navigate(`/prompt/edit?prompt=${prompt.id}`)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    <h3 className="font-medium">{prompt.id}</h3>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    v{prompt.version}
                  </Badge>
                </div>
                {prompt.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {prompt.description}
                  </p>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
