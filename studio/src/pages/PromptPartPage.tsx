import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Edit, Trash2, Save, X, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { cn } from '@/lib/utils';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import { usePromptPart, useUpdatePromptPart, useDeletePromptPart } from '@/hooks/useApi';

const categories = [
  'System Roles',
  'Formatting',
  'Examples',
  'Constraints',
  'Context Injection',
  'Output Instructions',
  'Utilities',
];

export function PromptPartPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { projectSlug } = useParams<{ projectSlug: string }>();
  const { projectId } = useAuthenticatedApi();
  const partId = searchParams.get('id');

  const { part, loading, refetch } = usePromptPart(projectId, partId);
  const { updatePart, loading: saving } = useUpdatePromptPart(projectId);
  const { deletePart } = useDeletePromptPart(projectId);

  const [isEditing, setIsEditing] = useState(false);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('System Roles');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [content, setContent] = useState('');

  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  useEffect(() => {
    if (!partId) {
      navigate(`/project/${projectSlug}/library`);
      return;
    }
  }, [partId, navigate, projectSlug]);

  useEffect(() => {
    if (part) {
      setName(part.name);
      setDescription(part.description || '');
      setCategory(part.category);
      setTags(part.tags || []);
      setContent(part.content);
    }
  }, [part]);

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
    if (!partId || !name.trim() || !content.trim()) return;

    try {
      await updatePart(partId, {
        name: name.trim(),
        description: description.trim() || undefined,
        category,
        tags,
        content: content.trim(),
      });
      setIsEditing(false);
      refetch?.();
    } catch (err) {
      console.error('Failed to update prompt part:', err);
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleCancel = () => {
    if (!part) return;
    setName(part.name);
    setDescription(part.description || '');
    setCategory(part.category);
    setTags(part.tags || []);
    setContent(part.content);
    setIsEditing(false);
  };

  const handleDelete = async () => {
    if (!partId) return;

    try {
      await deletePart(partId);
      navigate(`/project/${projectSlug}/library`);
    } catch (err) {
      console.error('Failed to delete prompt part:', err);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">Loading prompt part...</p>
      </div>
    );
  }

  if (!part) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">Prompt part not found</p>
      </div>
    );
  }

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
          <h1 className="text-2xl font-semibold">{isEditing ? name || 'Edit Prompt Part' : part.name}</h1>
        </div>
        <div className="flex items-center gap-3">
          {isEditing ? (
            <>
              <Button
                variant="ghost"
                onClick={handleCancel}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={saving || !name.trim() || !content.trim()}
                className="gap-2"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving...' : 'Save'}
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowDeleteDialog(true)}
                className="gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </Button>
              <Button
                size="sm"
                onClick={handleEdit}
                className="gap-2"
              >
                <Edit className="w-4 h-4" />
                Edit
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="max-w-5xl mx-auto p-8 space-y-8">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-sm font-medium">
              Name
            </Label>
            {isEditing ? (
              <>
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
              </>
            ) : (
              <p className="text-base">{part.name}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description" className="text-sm font-medium">
              Description
            </Label>
            {isEditing ? (
              <Textarea
                id="description"
                placeholder="Enter a description for your prompt part. This will help you and your team understand its purpose."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="min-h-[100px] resize-none text-base"
              />
            ) : (
              <p className="text-base text-muted-foreground">
                {part.description || 'No description'}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium">Category</Label>
            {isEditing ? (
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
            ) : (
              <Badge variant="secondary" className="text-sm">
                {part.category}
              </Badge>
            )}
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium">Tags</Label>
            {isEditing ? (
              <>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
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
                        <X className="w-3 h-3 ml-1" />
                      </Badge>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="flex flex-wrap gap-2">
                {tags.length > 0 ? (
                  tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-sm">
                      {tag}
                    </Badge>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No tags</p>
                )}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="content" className="text-sm font-medium">
                Content
              </Label>
              <Badge variant="outline" className="text-xs">
                v{part.version}
              </Badge>
            </div>
            {isEditing ? (
              <Textarea
                id="content"
                placeholder="You are a markdown formatting expert. Given any text, you will reformat it into clean, well-structured markdown..."
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="min-h-[300px] font-mono text-sm resize-none"
              />
            ) : (
              <pre className="min-h-[300px] font-mono text-sm bg-muted p-4 rounded-md overflow-auto whitespace-pre-wrap">
                {part.content}
              </pre>
            )}
          </div>
        </div>
      </div>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete prompt part</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{part.name}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}