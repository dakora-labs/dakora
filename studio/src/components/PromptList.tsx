import { useState } from 'react';
import { FileText, Search, Loader2, MessageSquare } from 'lucide-react';
import { usePrompts } from '../hooks/useApi';
import { NewPromptDialog } from './NewPromptDialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface PromptListProps {
  selectedPrompt: string | null;
  onSelectPrompt: (promptId: string | null) => void;
}

export function PromptList({ selectedPrompt, onSelectPrompt }: PromptListProps) {
  const { prompts, loading: promptsLoading, error: promptsError, refetch } = usePrompts();
  const [searchTerm, setSearchTerm] = useState('');

  const handlePromptCreated = (promptId: string) => {
    refetch();
    onSelectPrompt(promptId);
  };

  const filteredPrompts = prompts.filter(prompt =>
    prompt.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="w-full flex flex-col h-full">
      <div className="p-3">
        <div className="mb-4">
          <div className="text-xs font-medium text-muted-foreground mb-2 px-2">Create</div>
          <NewPromptDialog onPromptCreated={handlePromptCreated} variant="sidebar" />
        </div>

        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <Input
            type="text"
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 h-9"
          />
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="px-3 pb-3">
          {promptsLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          )}

          {promptsError && (
            <Card className="p-3 bg-destructive/10 border-destructive/20">
              <p className="text-sm text-destructive">{promptsError}</p>
            </Card>
          )}

          {!promptsLoading && !promptsError && filteredPrompts.length === 0 && (
            <div className="text-center py-8">
              <FileText className="w-12 h-12 mx-auto mb-3 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">No prompts found</p>
              {searchTerm && (
                <p className="text-xs text-muted-foreground mt-1">Try adjusting your search</p>
              )}
            </div>
          )}

          {filteredPrompts.map((promptId) => (
            <Button
              key={promptId}
              onClick={() => onSelectPrompt(promptId)}
              variant="ghost"
              className={cn(
                "w-full justify-start h-auto px-3 py-2.5 font-normal mb-1 rounded-lg",
                selectedPrompt === promptId
                  ? "bg-muted hover:bg-muted"
                  : "hover:bg-muted/50"
              )}
            >
              <div className="flex items-center gap-3 w-full min-w-0">
                <MessageSquare className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
                <span className="text-sm truncate">{promptId}</span>
              </div>
            </Button>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}