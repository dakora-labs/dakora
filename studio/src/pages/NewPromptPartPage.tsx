import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Save, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import { useCreatePromptPart } from '@/hooks/useApi';

const categories = [
  'System Roles',
  'Formatting',
  'Examples',
  'Constraints',
  'Context Injection',
  'Output Instructions',
  'Utilities',
];

export function NewPromptPartPage() {
  const navigate = useNavigate();
  const { projectSlug } = useParams<{ projectSlug: string }>();
  const { projectId } = useAuthenticatedApi();
  const { createPart, loading: saving } = useCreatePromptPart(projectId);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('System Roles');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [content, setContent] = useState('');

  const partKey = name
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '');

  const handleAddTag = (tag: string) => {
    const trimmed = tag.trim().toLowerCase();
    if (trimmed && !tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter(t => t !== tag));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      if (tagInput.trim()) {
        handleAddTag(tagInput);
        setTagInput('');
      }
    }
  };

  const handleSave = async () => {
    if (!partKey || !name.trim() || !content.trim()) return;

    try {
      await createPart({
        part_id: partKey,
        category,
        name: name.trim(),
        content: content.trim(),
        description: description.trim() || undefined,
        tags,
      });
      navigate(`/project/${projectSlug}/library`);
    } catch (err) {
      console.error('Failed to create prompt part:', err);
    }
  };

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="border-b border-border bg-card px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/project/${projectSlug}/library`)}
            className="gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
          <div className="h-4 w-px bg-border" />
          <h1 className="text-2xl font-semibold">New Prompt Part</h1>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            onClick={() => navigate(`/project/${projectSlug}/library`)}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || !name.trim() || !content.trim()}
            className="gap-2"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Part'}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="max-w-5xl mx-auto p-8 space-y-8">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-sm font-medium">
              Name
            </Label>
            <Input
              id="name"
              placeholder="e.g., Markdown Formatter"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="text-base"
            />
            {partKey && (
              <p className="text-sm text-muted-foreground">
                Part key: {partKey}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description" className="text-sm font-medium">
              Description
            </Label>
            <Textarea
              id="description"
              placeholder="Enter a description for your prompt part. This will help you and your team understand its purpose."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="min-h-[100px] resize-none text-base"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium">Category</Label>
            <div className="flex flex-wrap gap-2">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategory(cat)}
                  className={cn(
                    "px-4 py-2 rounded-full text-sm font-medium transition-colors",
                    category === cat
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground hover:bg-muted/80"
                  )}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="tags" className="text-sm font-medium">
              Tags
            </Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                id="tags"
                placeholder="Select or create tags..."
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={handleKeyDown}
                className="pl-10 text-base"
              />
            </div>
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-2 pt-2">
                {tags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="px-3 py-1 text-sm cursor-pointer hover:bg-secondary/80"
                    onClick={() => handleRemoveTag(tag)}
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="content" className="text-sm font-medium">
              Content
            </Label>
            <Textarea
              id="content"
              placeholder="You are a markdown formatting expert. Given any text, you will reformat it into clean, well-structured markdown..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="min-h-[300px] font-mono text-sm resize-none"
            />
          </div>
        </div>
      </div>
    </div>
  );
}