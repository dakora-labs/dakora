import { useState } from 'react';
import { FileText, Search, Loader2 } from 'lucide-react';
import { useTemplates } from '../hooks/useApi';
import { NewTemplateDialog } from './NewTemplateDialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface TemplateListProps {
  selectedTemplate: string | null;
  onSelectTemplate: (templateId: string | null) => void;
}

export function TemplateList({ selectedTemplate, onSelectTemplate }: TemplateListProps) {
  const { templates, loading: templatesLoading, error: templatesError, refetch } = useTemplates();
  const [searchTerm, setSearchTerm] = useState('');

  const handleTemplateCreated = (templateId: string) => {
    refetch();
    onSelectTemplate(templateId);
  };

  const filteredTemplates = templates.filter(template =>
    template.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="w-full flex flex-col h-full">
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Templates</h2>
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <Input
            type="text"
            placeholder="Search templates..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-2">
          {templatesLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          )}

          {templatesError && (
            <Card className="p-3 bg-destructive/10 border-destructive/20">
              <p className="text-sm text-destructive">{templatesError}</p>
            </Card>
          )}

          {!templatesLoading && !templatesError && filteredTemplates.length === 0 && (
            <div className="text-center py-8">
              <FileText className="w-12 h-12 mx-auto mb-3 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">No templates found</p>
              {searchTerm && (
                <p className="text-xs text-muted-foreground mt-1">Try adjusting your search</p>
              )}
            </div>
          )}

          {filteredTemplates.map((templateId) => (
            <Button
              key={templateId}
              onClick={() => onSelectTemplate(templateId)}
              variant={selectedTemplate === templateId ? "secondary" : "ghost"}
              className={cn(
                "w-full justify-start h-auto p-3 font-normal",
                selectedTemplate === templateId && "ring-2 ring-primary/20"
              )}
            >
              <div className="flex items-center w-full">
                <FileText className="w-4 h-4 mr-3 flex-shrink-0" />
                <span className="text-sm truncate">{templateId}</span>
              </div>
            </Button>
          ))}
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-border">
        <NewTemplateDialog onTemplateCreated={handleTemplateCreated} />
      </div>
    </div>
  );
}