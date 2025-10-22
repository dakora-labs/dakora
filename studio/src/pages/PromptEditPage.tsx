import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Edit, Trash2, Save, X, Plus, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
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
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import type { Template, InputSpec } from '@/types';

type InputType = 'string' | 'number' | 'boolean' | 'array<string>' | 'object';

interface VariableConfig {
  name: string;
  type: InputType;
}

export function PromptEditPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { api, projectId, projectSlug, contextLoading } = useAuthenticatedApi();
  const promptId = searchParams.get('prompt');

  const [prompt, setPrompt] = useState<Template | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [description, setDescription] = useState('');
  const [template, setTemplate] = useState('');
  const [variables, setVariables] = useState<VariableConfig[]>([]);
  const [showAddVariable, setShowAddVariable] = useState(false);
  const [newVarName, setNewVarName] = useState('');
  const [newVarType, setNewVarType] = useState<InputType>('string');

  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showUnusedVarsDialog, setShowUnusedVarsDialog] = useState(false);
  const [unusedVars, setUnusedVars] = useState<string[]>([]);

  useEffect(() => {
    if (contextLoading || !projectId || !projectSlug) return;

    if (!promptId) {
      navigate(`/project/${projectSlug}/prompts`);
      return;
    }

    const loadPrompt = async () => {
      try {
        const data = await api.getPrompt(projectId, promptId);
        setPrompt(data);
        setDescription(data.description || '');
        setTemplate(data.template);

        const vars: VariableConfig[] = Object.entries(data.inputs || {}).map(([name, spec]) => ({
          name,
          type: spec.type as InputType,
        }));
        setVariables(vars);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load prompt');
      } finally {
        setLoading(false);
      }
    };

    loadPrompt();
  }, [promptId, navigate, api, projectId, contextLoading]);

  const handleAddVariable = () => {
    if (!newVarName.trim()) return;

    if (variables.some(v => v.name === newVarName.trim())) {
      setError('Variable with this name already exists');
      return;
    }

    setVariables([...variables, { name: newVarName.trim(), type: newVarType }]);
    setNewVarName('');
    setNewVarType('string');
    setShowAddVariable(false);
    setError('');
  };

  const removeVariable = (name: string) => {
    setVariables(variables.filter(v => v.name !== name));
  };

  const validateTemplate = (): string[] => {
    const unused: string[] = [];
    for (const v of variables) {
      if (v.name.trim()) {
        const regex = new RegExp(`{{\\s*${v.name.trim()}\\s*}}`, 'g');
        if (!regex.test(template)) {
          unused.push(v.name.trim());
        }
      }
    }
    return unused;
  };

  const performSave = async () => {
    if (!promptId || !projectId) return;

    const inputs: Record<string, InputSpec> = {};
    for (const v of variables) {
      inputs[v.name] = {
        type: v.type,
        required: true,
      };
    }

    try {
      setSaving(true);
      const updated = await api.updatePrompt(projectId, promptId, {
        description: description.trim() || undefined,
        template: template,
        inputs,
      });
      setPrompt(updated);
      setIsEditing(false);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update prompt');
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    setError('');

    for (const v of variables) {
      if (!v.name.trim()) {
        setError('All variables must have a name');
        return;
      }
    }

    const unused = validateTemplate();
    if (unused.length > 0) {
      setUnusedVars(unused);
      setShowUnusedVarsDialog(true);
      return;
    }

    await performSave();
  };

  const handleSaveAnyway = async () => {
    setShowUnusedVarsDialog(false);
    await performSave();
  };

  const handleDelete = async () => {
    if (!promptId || !projectId || !projectSlug) return;

    try {
      await api.deletePrompt(projectId, promptId);
      navigate(`/project/${projectSlug}/prompts`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete prompt');
      setShowDeleteDialog(false);
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleCancel = () => {
    if (!prompt) return;

    setDescription(prompt.description || '');
    setTemplate(prompt.template);
    const vars: VariableConfig[] = Object.entries(prompt.inputs || {}).map(([name, spec]) => ({
      name,
      type: spec.type as InputType,
    }));
    setVariables(vars);
    setIsEditing(false);
    setError('');
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">Loading prompt...</p>
      </div>
    );
  }

  if (!prompt) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">Prompt not found</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="border-b border-border bg-card px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/project/${projectSlug}/prompts`)}
            className="gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
          <div className="h-4 w-px bg-border" />
          <h1 className="text-lg font-semibold">{prompt.id}</h1>
          <Badge variant="outline" className="text-xs">v{prompt.version}</Badge>
        </div>
        <div className="flex items-center gap-2">
          {isEditing ? (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCancel}
                className="gap-2"
              >
                <X className="w-4 h-4" />
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={saving}
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

      {error && (
        <div className="bg-destructive/10 border-b border-destructive/20 px-4 py-2">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      <div className="flex-1 overflow-hidden">
        <div className="h-full grid grid-cols-12 gap-0">
          <div className="col-span-3 border-r border-border overflow-auto">
            <div className="p-4 space-y-4">
              <div className="space-y-2">
                <Label className="text-xs font-medium">Name</Label>
                <p className="text-sm">{prompt.id}</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description" className="text-xs font-medium">
                  Description
                </Label>
                {isEditing ? (
                  <Textarea
                    id="description"
                    placeholder="What does this prompt do?"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="min-h-[80px] resize-none"
                  />
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {prompt.description || 'No description'}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-medium">Version</Label>
                  <Badge variant="secondary" className="text-xs">v{prompt.version}</Badge>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-medium">Variables</Label>
                  {isEditing && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowAddVariable(true)}
                      className="h-7 gap-1.5"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add
                    </Button>
                  )}
                </div>

                {isEditing && showAddVariable && (
                  <Card className="p-3 space-y-2 border-primary">
                    <Input
                      placeholder="e.g., city"
                      value={newVarName}
                      onChange={(e) => setNewVarName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleAddVariable();
                        if (e.key === 'Escape') {
                          setShowAddVariable(false);
                          setNewVarName('');
                        }
                      }}
                      className="h-8 text-sm"
                      autoFocus
                    />
                    <Select value={newVarType} onValueChange={(value) => setNewVarType(value as InputType)}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="string">String</SelectItem>
                        <SelectItem value="number">Number</SelectItem>
                        <SelectItem value="boolean">Boolean</SelectItem>
                        <SelectItem value="array<string>">Array</SelectItem>
                        <SelectItem value="object">Object</SelectItem>
                      </SelectContent>
                    </Select>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={handleAddVariable}
                        className="flex-1 h-7"
                      >
                        Add
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setShowAddVariable(false);
                          setNewVarName('');
                        }}
                        className="flex-1 h-7"
                      >
                        Cancel
                      </Button>
                    </div>
                  </Card>
                )}

                {variables.length > 0 && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {variables.map((variable) => (
                      <Badge
                        key={variable.name}
                        variant="secondary"
                        className="gap-1.5 pl-2.5 pr-1.5 py-1 text-xs"
                      >
                        <span>{variable.name}</span>
                        <span className="text-muted-foreground">({variable.type})</span>
                        {isEditing && (
                          <button
                            onClick={() => removeVariable(variable.name)}
                            className="ml-1 hover:bg-muted-foreground/20 rounded-sm p-0.5"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        )}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="col-span-9 overflow-auto">
            <div className="p-4">
              <div className="space-y-2">
                <Label htmlFor="template" className="text-xs font-medium">
                  Template
                </Label>
                {isEditing ? (
                  <Textarea
                    id="template"
                    placeholder="Write your prompt template here. Use {{ variable_name }} for dynamic inputs."
                    value={template}
                    onChange={(e) => setTemplate(e.target.value)}
                    className="min-h-[calc(100vh-180px)] font-mono text-sm resize-none"
                  />
                ) : (
                  <pre className="min-h-[calc(100vh-180px)] font-mono text-sm bg-muted p-4 rounded-md overflow-auto whitespace-pre-wrap">
                    {prompt.template}
                  </pre>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete prompt</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{prompt.id}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={showUnusedVarsDialog} onOpenChange={setShowUnusedVarsDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              <AlertDialogTitle>Not all variables are used</AlertDialogTitle>
            </div>
            <AlertDialogDescription>
              The following variables are declared but not used in the template:
              <ul className="mt-2 list-disc list-inside space-y-1">
                {unusedVars.map((varName) => (
                  <li key={varName} className="font-mono text-sm">
                    {varName}
                  </li>
                ))}
              </ul>
              <p className="mt-3">
                Do you want to save anyway?
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleSaveAnyway} disabled={saving}>
              {saving ? 'Saving...' : 'Save Anyway'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
