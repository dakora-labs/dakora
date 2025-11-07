import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Save, X, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card } from '@/components/ui/card';
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
import { useFeedbackContext } from '@/contexts/FeedbackContext';
import { PromptPartsPanel } from '@/components/PromptPartsPanel';
import { RichTemplateEditor, type RichTemplateEditorRef } from '@/components/RichTemplateEditor';
import type { InputSpec } from '@/types';

type InputType = 'string' | 'number' | 'boolean' | 'array<string>' | 'object';

interface VariableConfig {
  name: string;
  type: InputType;
}

export function NewPromptPage() {
  const navigate = useNavigate();
  const { api, projectId, projectSlug, contextLoading } = useAuthenticatedApi();
  const { trackPromptCreated } = useFeedbackContext();
  const editorRef = useRef<RichTemplateEditorRef>(null);
  const [id, setId] = useState('');
  const [description, setDescription] = useState('');
  const [template, setTemplate] = useState('');
  const [variables, setVariables] = useState<VariableConfig[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [showUnusedVarsDialog, setShowUnusedVarsDialog] = useState(false);
  const [unusedVars, setUnusedVars] = useState<string[]>([]);
  const [showAddVariable, setShowAddVariable] = useState(false);
  const [newVarName, setNewVarName] = useState('');
  const [newVarType, setNewVarType] = useState<InputType>('string');

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
    if (contextLoading || !projectId || !projectSlug) {
      setError('Project not loaded yet');
      return;
    }

    const inputs: Record<string, InputSpec> = {};
    for (const v of variables) {
      inputs[v.name] = {
        type: v.type,
        required: true,
      };
    }

    try {
      setSaving(true);
      await api.createPrompt(projectId, {
        id: id.trim(),
        version: '1.0.0',
        description: description.trim() || undefined,
        template: template,
        inputs,
      });
      trackPromptCreated();
      navigate(`/project/${projectSlug}/prompt/edit?prompt=${id.trim()}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create prompt');
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    setError('');

    if (!id.trim()) {
      setError('Name is required');
      return;
    }

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

  const getUsedParts = useCallback((): Array<{ category: string; partId: string }> => {
    const includePattern = /{%\s*include\s+"([^"]+)"\s*%}/g;
    const parts: Array<{ category: string; partId: string }> = [];
    let match;

    while ((match = includePattern.exec(template)) !== null) {
      const [category, partId] = match[1].split('/');
      if (category && partId) {
        parts.push({ category, partId });
      }
    }

    return parts;
  }, [template]);

  const handleInsertPart = useCallback((category: string, partId: string) => {
    const insertText = `{% include "${category}/${partId}" %}`;
    editorRef.current?.insertAtCursor(insertText);
  }, []);

  const handleDeletePart = useCallback((category: string, partId: string) => {
    const partPattern = new RegExp(
      `{%\\s*include\\s+"${category}/${partId}"\\s*%}`,
      'g'
    );
    setTemplate(template.replace(partPattern, ''));
  }, [template]);

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="border-b border-border bg-card px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => projectSlug && navigate(`/project/${projectSlug}/prompts`)}
            className="gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
          <div className="h-4 w-px bg-border" />
          <h1 className="text-lg font-semibold">{id.trim() || 'New Prompt'}</h1>
          <Badge variant="outline" className="text-xs">Draft</Badge>
        </div>
        <Button onClick={handleSave} disabled={saving} className="gap-2">
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </div>

      {error && (
        <div className="bg-destructive/10 border-b border-destructive/20 px-4 py-2">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      <div className="flex-1 overflow-hidden">
        <div className="h-full grid grid-cols-12 gap-0">
          <div className="col-span-2 border-r border-border overflow-auto">
            <div className="p-4 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="prompt-name" className="text-xs font-medium">
                  Name
                </Label>
                <Input
                  id="prompt-name"
                  placeholder="e.g., summarizer"
                  value={id}
                  onChange={(e) => setId(e.target.value)}
                  className="h-9"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description" className="text-xs font-medium">
                  Description
                </Label>
                <Textarea
                  id="description"
                  placeholder="What does this prompt do?"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="min-h-[80px] resize-none"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-medium">Version</Label>
                  <Badge variant="secondary" className="text-xs">1.0.0</Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Initial version
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-medium">Variables</Label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowAddVariable(true)}
                    className="h-7 gap-1.5"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Add
                  </Button>
                </div>

                {showAddVariable && (
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
                        <button
                          onClick={() => removeVariable(variable.name)}
                          className="ml-1 hover:bg-muted-foreground/20 rounded-sm p-0.5"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="col-span-7 overflow-auto">
            <div className="p-4">
              <div className="space-y-2">
                <Label htmlFor="template" className="text-xs font-medium">
                  Template
                </Label>
                <RichTemplateEditor
                  ref={editorRef}
                  value={template}
                  onChange={setTemplate}
                  placeholder="Write your prompt template here. Use {{ variable_name }} for dynamic inputs."
                  className="min-h-[calc(100vh-180px)]"
                />
              </div>
            </div>
          </div>

          <div className="col-span-3 border-l border-border overflow-hidden">
            <PromptPartsPanel
              projectId={projectId}
              onInsertPart={handleInsertPart}
              usedParts={getUsedParts()}
              onDeletePart={handleDeletePart}
            />
          </div>
        </div>
      </div>

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
