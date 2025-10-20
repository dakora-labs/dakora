import { useState, useEffect, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import { Play, AlertCircle, CheckCircle, FileText, Loader2, Info, Code2, Edit3, Save, X, Plus, Trash2 } from 'lucide-react';
import { usePrompt, useRender, useUpdatePrompt } from '../hooks/useApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import type { InputSpec } from '../types';

interface PromptEditorProps {
  promptId: string | null;
}

export function PromptEditor({ promptId }: PromptEditorProps) {
  const { prompt, loading, error, refetch } = usePrompt(promptId);
  const { render, loading: renderLoading, error: renderError, clearError } = useRender();
  const { updatePrompt, loading: updateLoading, error: updateError, clearError: clearUpdateError } = useUpdatePrompt();

  const [templateContent, setTemplateContent] = useState('');
  const [inputs, setInputs] = useState<Record<string, unknown>>({});
  const [renderResult, setRenderResult] = useState<string>('');
  const [showPreview, setShowPreview] = useState(false);

  // Edit mode states
  const [isEditMode, setIsEditMode] = useState(false);
  const [originalContent, setOriginalContent] = useState('');
  const [isDirty, setIsDirty] = useState(false);

  // Input parameters editing states
  const [editedInputs, setEditedInputs] = useState<Record<string, InputSpec>>({});
  const [showAddInputDialog, setShowAddInputDialog] = useState(false);
  const [newInputName, setNewInputName] = useState('');
  const [newInputType, setNewInputType] = useState<InputSpec['type']>('string');
  const [newInputRequired, setNewInputRequired] = useState(true);
  const [newInputDefault, setNewInputDefault] = useState<string>('');

  useEffect(() => {
    if (prompt) {
      setTemplateContent(prompt.template);
      setOriginalContent(prompt.template);
      setIsEditMode(false);
      setIsDirty(false);
      setEditedInputs(prompt.inputs);
      // Initialize inputs with defaults
      const defaultInputs: Record<string, unknown> = {};
      Object.entries(prompt.inputs).forEach(([key, spec]) => {
        if (spec.default !== undefined) {
          defaultInputs[key] = spec.default;
        } else if (spec.required) {
          // Set empty values for required inputs
          switch (spec.type) {
            case 'string':
              defaultInputs[key] = '';
              break;
            case 'number':
              defaultInputs[key] = 0;
              break;
            case 'boolean':
              defaultInputs[key] = false;
              break;
            case 'array<string>':
              defaultInputs[key] = [];
              break;
            case 'object':
              defaultInputs[key] = {};
              break;
          }
        }
      });
      setInputs(defaultInputs);
      setRenderResult('');
      setShowPreview(false);
    }
  }, [prompt]);

  useEffect(() => {
    clearError();
  }, [templateContent, inputs, clearError]);

  // Edit mode handlers
  const handleEnterEditMode = useCallback(() => {
    setIsEditMode(true);
    setOriginalContent(templateContent);
    setIsDirty(false);
    clearUpdateError();
  }, [templateContent, clearUpdateError]);

  const handleContentChange = useCallback((value: string | undefined) => {
    const newContent = value || '';
    setTemplateContent(newContent);
    setIsDirty(newContent !== originalContent || JSON.stringify(editedInputs) !== JSON.stringify(prompt?.inputs || {}));
  }, [originalContent, editedInputs, prompt]);

  const handleSave = useCallback(async () => {
    if (!prompt || !isDirty) return;

    try {
      await updatePrompt(prompt.id, {
        template: templateContent,
        description: prompt.description,
        version: prompt.version,
        inputs: editedInputs,
        metadata: prompt.metadata,
      });

      setOriginalContent(templateContent);
      setIsDirty(false);
      setIsEditMode(false);

      // Refresh the template to get the latest version
      if (refetch) {
        await refetch();
      }
    } catch (error) {
      console.error('Save error:', error);
    }
  }, [prompt, templateContent, editedInputs, isDirty, updatePrompt, refetch]);

  const handleCancel = useCallback(() => {
    if (isDirty) {
      const confirmed = window.confirm('You have unsaved changes. Are you sure you want to cancel?');
      if (!confirmed) return;
    }

    setTemplateContent(originalContent);
    setEditedInputs(prompt?.inputs || {});
    setIsDirty(false);
    setIsEditMode(false);
    clearUpdateError();
  }, [isDirty, originalContent, prompt, clearUpdateError]);

  // Keyboard shortcuts
  useEffect(() => {
    if (!isEditMode) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey || event.metaKey) {
        if (event.key === 's') {
          event.preventDefault();
          if (isDirty) {
            handleSave();
          }
        }
      }

      if (event.key === 'Escape') {
        event.preventDefault();
        handleCancel();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isEditMode, isDirty, handleSave, handleCancel]);

  // Input parameter management functions
  const handleAddInput = useCallback(() => {
    if (!newInputName.trim()) return;

    if (editedInputs[newInputName]) {
      alert('An input with this name already exists.');
      return;
    }

    const newSpec: InputSpec = {
      type: newInputType,
      required: newInputRequired,
    };

    // Add default value if provided
    if (newInputDefault) {
      try {
        switch (newInputType) {
          case 'string':
            newSpec.default = newInputDefault;
            break;
          case 'number':
            newSpec.default = parseFloat(newInputDefault);
            break;
          case 'boolean':
            newSpec.default = newInputDefault.toLowerCase() === 'true';
            break;
          case 'array<string>':
            newSpec.default = newInputDefault.split('\n').filter(Boolean);
            break;
          case 'object':
            newSpec.default = JSON.parse(newInputDefault);
            break;
        }
      } catch (error) {
        alert('Invalid default value for the selected type.');
        return;
      }
    }

    setEditedInputs(prev => ({
      ...prev,
      [newInputName]: newSpec,
    }));

    // Check if we need to mark as dirty
    setIsDirty(
      templateContent !== originalContent ||
      JSON.stringify({...editedInputs, [newInputName]: newSpec}) !== JSON.stringify(prompt?.inputs || {})
    );

    // Reset dialog form
    setNewInputName('');
    setNewInputType('string');
    setNewInputRequired(true);
    setNewInputDefault('');
    setShowAddInputDialog(false);
  }, [newInputName, newInputType, newInputRequired, newInputDefault, editedInputs, templateContent, originalContent,prompt]);

  const handleRemoveInput = useCallback((inputName: string) => {
    const confirmed = window.confirm(`Are you sure you want to remove the input "${inputName}"?`);
    if (!confirmed) return;

    const newEditedInputs = { ...editedInputs };
    delete newEditedInputs[inputName];
    setEditedInputs(newEditedInputs);

    // Remove from current inputs too
    setInputs(prev => {
      const newInputs = { ...prev };
      delete newInputs[inputName];
      return newInputs;
    });

    // Check if we need to mark as dirty
    setIsDirty(
      templateContent !== originalContent ||
      JSON.stringify(newEditedInputs) !== JSON.stringify(prompt?.inputs || {})
    );
  }, [editedInputs, templateContent, originalContent,prompt]);

  const handleInputSpecChange = useCallback((inputName: string, field: keyof InputSpec, value: any) => {
    setEditedInputs(prev => ({
      ...prev,
      [inputName]: {
        ...prev[inputName],
        [field]: value,
      }
    }));

    // Check if we need to mark as dirty
    const updatedInputs = {
      ...editedInputs,
      [inputName]: {
        ...editedInputs[inputName],
        [field]: value,
      }
    };

    setIsDirty(
      templateContent !== originalContent ||
      JSON.stringify(updatedInputs) !== JSON.stringify(prompt?.inputs || {})
    );
  }, [editedInputs, templateContent, originalContent,prompt]);

  const handleRender = async () => {
    if (!prompt) return;

    try {
      const response = await render(prompt.id, inputs);
      setRenderResult(response.rendered);
      setShowPreview(true);
    } catch (error) {
      console.error('Render error:', error);
    }
  };

  const handleInputChange = (key: string, value: unknown) => {
    setInputs(prev => ({ ...prev, [key]: value }));
  };

  const renderInputField = (key: string, spec: any) => {
    const value = inputs[key];

    switch (spec.type) {
      case 'string':
        return (
          <Textarea
            value={(value as string) || ''}
            onChange={(e) => handleInputChange(key, e.target.value)}
            placeholder={`Enter ${key}...`}
            rows={3}
          />
        );

      case 'number':
        return (
          <Input
            type="number"
            value={(value as number) || ''}
            onChange={(e) => handleInputChange(key, parseFloat(e.target.value) || 0)}
            placeholder={`Enter ${key}...`}
          />
        );

      case 'boolean':
        return (
          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2">
              <input
                type="radio"
                name={`${key}-bool`}
                checked={(value as boolean) === true}
                onChange={() => handleInputChange(key, true)}
                className="text-primary"
              />
              <span className="text-sm">True</span>
            </label>
            <label className="flex items-center space-x-2">
              <input
                type="radio"
                name={`${key}-bool`}
                checked={(value as boolean) === false}
                onChange={() => handleInputChange(key, false)}
                className="text-primary"
              />
              <span className="text-sm">False</span>
            </label>
          </div>
        );

      case 'array<string>':
        return (
          <Textarea
            value={Array.isArray(value) ? (value as string[]).join('\n') : ''}
            onChange={(e) => handleInputChange(key, e.target.value.split('\n').filter(Boolean))}
            placeholder={`Enter ${key} (one per line)...`}
            rows={3}
          />
        );

      case 'object':
        return (
          <Textarea
            value={typeof value === 'object' ? JSON.stringify(value, null, 2) : ''}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value);
                handleInputChange(key, parsed);
              } catch {
                // Invalid JSON, ignore
              }
            }}
            className="font-mono"
            placeholder={`Enter ${key} as JSON...`}
            rows={4}
          />
        );

      default:
        return null;
    }
  };

  if (!promptId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-muted/10">
        <Card className="w-96 text-center">
          <CardContent className="pt-6">
            <FileText className="w-16 h-16 text-muted-foreground/50 mx-auto mb-4" />
            <CardTitle className="mb-2">No Prompt Selected</CardTitle>
            <CardDescription>
              Select a prompt from the sidebar to start editing and testing
            </CardDescription>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-muted/10">
        <Card className="w-96 text-center">
          <CardContent className="pt-6">
            <Loader2 className="w-12 h-12 text-primary mx-auto mb-4 animate-spin" />
            <CardTitle className="mb-2">Loading Prompt</CardTitle>
            <CardDescription>Please wait while we load the prompt...</CardDescription>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center bg-muted/10">
        <Card className="w-96 text-center">
          <CardContent className="pt-6">
            <AlertCircle className="w-16 h-16 text-destructive mx-auto mb-4" />
            <CardTitle className="mb-2">Error Loading Prompt</CardTitle>
            <CardDescription className="text-destructive">{error}</CardDescription>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!prompt) return null;

  return (
    <div className="flex-1 flex flex-col h-full bg-background">
      {/* Header */}
      <div className="border-b border-border px-4 md:px-6 py-4 bg-card">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-2">
              <h1 className="text-lg md:text-xl font-semibold truncate">{prompt.id}</h1>
              <Badge variant="secondary">{prompt.version}</Badge>
              {isEditMode && (
                <Badge variant="default" className="bg-blue-600">
                  {isDirty ? 'Editing (unsaved)' : 'Editing'}
                </Badge>
              )}
            </div>
            {prompt.description && (
              <p className="text-sm text-muted-foreground">{prompt.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {isEditMode ? (
              <>
                <Button
                  onClick={handleCancel}
                  variant="outline"
                  size="sm"
                  disabled={updateLoading}
                >
                  <X className="w-4 h-4 mr-2" />
                  <span className="hidden sm:inline">Cancel</span>
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={!isDirty || updateLoading}
                  size="sm"
                  className="bg-green-600 hover:bg-green-700"
                >
                  {updateLoading ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4 mr-2" />
                  )}
                  {updateLoading ? 'Saving...' : 'Save'}
                </Button>
              </>
            ) : (
              <Button
                onClick={handleEnterEditMode}
                variant="outline"
                size="sm"
              >
                <Edit3 className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Edit</span>
              </Button>
            )}
            <Button
              onClick={handleRender}
              disabled={renderLoading}
            >
              {renderLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  <span className="hidden sm:inline">Rendering...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  <span className="hidden sm:inline">Render</span>
                </>
              )}
            </Button>
          </div>
        </div>
        {updateError && (
          <div className="mt-3 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
            <p className="text-sm text-destructive">{updateError}</p>
          </div>
        )}
      </div>

      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Left Panel - Prompt & Inputs */}
        <div className="flex-1 flex flex-col border-b lg:border-r lg:border-b-0 border-border">
          {/* Template Editor */}
          <div className="flex-1 bg-card">
            <div className="px-4 py-3 border-b border-border bg-muted/30">
              <div className="flex items-center gap-2">
                <Code2 className="w-4 h-4" />
                <h3 className="text-sm font-medium">Template</h3>
                {isEditMode ? (
                  <Badge variant="outline" className="text-xs">Editing</Badge>
                ) : (
                  <Badge variant="outline" className="text-xs">Read-only</Badge>
                )}
              </div>
            </div>
            <div className="h-64 lg:h-80">
              <Editor
                height="100%"
                language="handlebars"
                value={templateContent}
                onChange={handleContentChange}
                options={{
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                  lineNumbers: 'on',
                  fontSize: 14,
                  readOnly: !isEditMode,
                  theme: 'vs',
                }}
              />
            </div>
          </div>

          {/* Inputs Panel */}
          <div className="flex-1 min-h-0 border-t border-border bg-muted/30 flex flex-col">
            <div className="px-4 py-3 border-b border-border bg-muted/30 flex-shrink-0">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Prompt Inputs</h3>
                <div className="flex items-center gap-2">
                  {Object.keys(editedInputs).length > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {Object.keys(editedInputs).length} input{Object.keys(editedInputs).length !== 1 ? 's' : ''}
                    </Badge>
                  )}
                  {isEditMode && (
                    <Dialog open={showAddInputDialog} onOpenChange={setShowAddInputDialog}>
                      <DialogTrigger asChild>
                        <Button variant="outline" size="sm">
                          <Plus className="w-4 h-4" />
                          <span className="hidden sm:inline ml-1">Add</span>
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="sm:max-w-md">
                        <DialogHeader>
                          <DialogTitle>Add Input Parameter</DialogTitle>
                          <DialogDescription>
                            Add a new input parameter to your prompt.
                          </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4">
                          <div>
                            <Label htmlFor="input-name">Name</Label>
                            <Input
                              id="input-name"
                              value={newInputName}
                              onChange={(e) => setNewInputName(e.target.value)}
                              placeholder="input_name"
                            />
                          </div>
                          <div>
                            <Label htmlFor="input-type">Type</Label>
                            <Select value={newInputType} onValueChange={(value) => setNewInputType(value as InputSpec['type'])}>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="string">String</SelectItem>
                                <SelectItem value="number">Number</SelectItem>
                                <SelectItem value="boolean">Boolean</SelectItem>
                                <SelectItem value="array<string>">Array of Strings</SelectItem>
                                <SelectItem value="object">Object</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              id="input-required"
                              checked={newInputRequired}
                              onChange={(e) => setNewInputRequired(e.target.checked)}
                            />
                            <Label htmlFor="input-required">Required</Label>
                          </div>
                          <div>
                            <Label htmlFor="input-default">Default Value (optional)</Label>
                            <Textarea
                              id="input-default"
                              value={newInputDefault}
                              onChange={(e) => setNewInputDefault(e.target.value)}
                              placeholder={
                                newInputType === 'object' ? '{"key": "value"}' :
                                newInputType === 'array<string>' ? 'item1\nitem2' :
                                newInputType === 'boolean' ? 'true' :
                                'default value'
                              }
                              rows={2}
                            />
                          </div>
                        </div>
                        <DialogFooter>
                          <Button variant="outline" onClick={() => setShowAddInputDialog(false)}>
                            Cancel
                          </Button>
                          <Button onClick={handleAddInput}>Add Input</Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                  )}
                </div>
              </div>
            </div>
            <ScrollArea className="flex-1 min-h-0">
              <div className="p-4">
                {Object.keys(editedInputs).length === 0 ? (
                  <div className="text-center py-8">
                    <Info className="w-8 h-8 mx-auto mb-3 text-muted-foreground/50" />
                    <p className="text-sm text-muted-foreground">No inputs defined for this prompt</p>
                    {isEditMode && (
                      <p className="text-xs text-muted-foreground mt-2">Click "Add" to create your first input parameter</p>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {Object.entries(editedInputs).map(([key, spec]) => (
                      <div key={key} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="text-sm font-medium">
                            {key}
                            {spec.required && <span className="text-destructive ml-1">*</span>}
                          </label>
                          <div className="flex items-center gap-1">
                            <Badge variant="outline" className="text-xs">
                              {spec.type}
                            </Badge>
                            {!spec.required && (
                              <Badge variant="secondary" className="text-xs">
                                optional
                              </Badge>
                            )}
                            {isEditMode && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleRemoveInput(key)}
                                className="h-6 w-6 p-0 hover:bg-destructive/10"
                              >
                                <Trash2 className="w-3 h-3 text-destructive" />
                              </Button>
                            )}
                          </div>
                        </div>

                        {isEditMode ? (
                          <div className="space-y-2 p-3 bg-muted/50 rounded-md border">
                            <div className="flex items-center gap-2">
                              <Label className="text-xs">Type:</Label>
                              <Select
                                value={spec.type}
                                onValueChange={(value) => handleInputSpecChange(key, 'type', value as InputSpec['type'])}
                              >
                                <SelectTrigger className="h-7 text-xs">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="string">String</SelectItem>
                                  <SelectItem value="number">Number</SelectItem>
                                  <SelectItem value="boolean">Boolean</SelectItem>
                                  <SelectItem value="array<string>">Array of Strings</SelectItem>
                                  <SelectItem value="object">Object</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="flex items-center space-x-2">
                              <input
                                type="checkbox"
                                id={`${key}-required`}
                                checked={spec.required}
                                onChange={(e) => handleInputSpecChange(key, 'required', e.target.checked)}
                                className="text-xs"
                              />
                              <Label htmlFor={`${key}-required`} className="text-xs">Required</Label>
                            </div>
                          </div>
                        ) : (
                          <>
                            {renderInputField(key, spec)}
                            {spec.default !== undefined && (
                              <p className="text-xs text-muted-foreground">
                                Default: {String(spec.default)}
                              </p>
                            )}
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        </div>

        {/* Right Panel - Preview */}
        <div className="flex-1 bg-card flex flex-col">
          <div className="px-4 py-3 border-b border-border bg-muted/30">
            <h3 className="text-sm font-medium">Preview</h3>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-4">
              {renderError && (
                <Card className="mb-4 bg-destructive/10 border-destructive/20">
                  <CardContent className="pt-4">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
                      <div>
                        <h4 className="text-sm font-medium text-destructive mb-1">Render Error</h4>
                        <p className="text-sm text-destructive/80">{renderError}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {!showPreview && !renderError && (
                <div className="text-center py-12">
                  <Play className="w-16 h-16 mx-auto mb-4 text-muted-foreground/30" />
                  <h3 className="text-lg font-medium mb-2">Ready to Render</h3>
                  <p className="text-sm text-muted-foreground">
                    Fill in the prompt inputs and click "Render" to preview the output
                  </p>
                </div>
              )}

              {showPreview && renderResult && (
                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-green-500" />
                      <CardTitle className="text-green-700">Rendered Successfully</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="bg-muted rounded-md p-4 border">
                      <pre className="text-sm whitespace-pre-wrap font-mono text-foreground leading-relaxed">
                        {renderResult}
                      </pre>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  );
}