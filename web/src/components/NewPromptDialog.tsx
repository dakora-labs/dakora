import { useState } from 'react';
import { Plus, Loader2, X, Save } from 'lucide-react';
import { useCreatePrompt } from '../hooks/useApi';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';

interface InputDefinition {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array<string>' | 'object';
  required: boolean;
  default?: string;
}

interface NewPromptDialogProps {
  onPromptCreated?: (promptId: string) => void;
  variant?: 'default' | 'sidebar';
}

export function NewPromptDialog({ onPromptCreated, variant = 'default' }: NewPromptDialogProps) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    id: '',
    version: '1.0.0',
    description: '',
    template: '',
    metadata: { tags: [] as string[] }
  });
  const [inputs, setInputs] = useState<InputDefinition[]>([]);
  const [newInput, setNewInput] = useState<InputDefinition>({
    name: '',
    type: 'string',
    required: true,
    default: ''
  });

  const { createPrompt, loading, error, clearError } = useCreatePrompt();

  const resetForm = () => {
    setStep(1);
    setFormData({
      id: '',
      version: '1.0.0',
      description: '',
      template: '',
      metadata: { tags: [] }
    });
    setInputs([]);
    setNewInput({
      name: '',
      type: 'string',
      required: true,
      default: ''
    });
    clearError();
  };

  const handleClose = () => {
    setOpen(false);
    resetForm();
  };

  const addInput = () => {
    if (newInput.name && !inputs.some(input => input.name === newInput.name)) {
      setInputs([...inputs, { ...newInput }]);
      setNewInput({
        name: '',
        type: 'string',
        required: true,
        default: ''
      });
    }
  };

  const removeInput = (index: number) => {
    setInputs(inputs.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    try {
      const templateData = {
        id: formData.id,
        version: formData.version,
        description: formData.description,
        template: formData.template,
        inputs: inputs.reduce((acc, input) => {
          acc[input.name] = {
            type: input.type,
            required: input.required,
            ...(input.default && input.default !== '' ? { default: parseInputValue(input.default, input.type) } : {})
          };
          return acc;
        }, {} as Record<string, { type: string; required: boolean; default?: unknown }>),
        metadata: formData.metadata
      };

      await createPrompt(templateData);
      onPromptCreated?.(formData.id);
      handleClose();
    } catch (err) {
      console.error('Failed to create template:', err);
    }
  };

  const parseInputValue = (value: string, type: string): unknown => {
    switch (type) {
      case 'number':
        return parseFloat(value);
      case 'boolean':
        return value.toLowerCase() === 'true';
      case 'array<string>':
        return value.split(',').map(s => s.trim()).filter(Boolean);
      case 'object':
        try {
          return JSON.parse(value);
        } catch {
          return {};
        }
      default:
        return value;
    }
  };

  const canProceedToStep2 = formData.id && formData.template;
  const canSave = canProceedToStep2;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {variant === 'sidebar' ? (
          <Button
            variant="ghost"
            className="w-full justify-start h-auto px-3 py-2.5 font-normal rounded-lg hover:bg-muted/50"
          >
            <div className="flex items-center gap-3 w-full min-w-0">
              <Plus className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
              <span className="text-sm">Prompt</span>
            </div>
          </Button>
        ) : (
          <Button variant="outline" className="w-full" size="sm">
            <Plus className="w-4 h-4 mr-2" />
            New Prompt
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Prompt</DialogTitle>
          <DialogDescription>
            Create a new prompt with inputs and metadata.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Step 1: Basic Information */}
          <Card className={step === 1 ? 'ring-2 ring-primary/20' : ''}>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Badge variant={step === 1 ? 'default' : 'secondary'}>1</Badge>
                Prompt Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="template-id">Prompt ID *</Label>
                  <Input
                    id="template-id"
                    placeholder="my-prompt"
                    value={formData.id}
                    onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="template-version">Version</Label>
                  <Input
                    id="template-version"
                    value={formData.version}
                    onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="template-description">Description</Label>
                <Input
                  id="template-description"
                  placeholder="Brief description of what this template does"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="template-content">Prompt Content *</Label>
                <Textarea
                  id="template-content"
                  placeholder="Enter your Jinja2 template here..."
                  className="min-h-32 font-mono"
                  value={formData.template}
                  onChange={(e) => setFormData({ ...formData, template: e.target.value })}
                />
              </div>
            </CardContent>
          </Card>

          {/* Step 2: Input Definitions */}
          <Card className={step === 2 ? 'ring-2 ring-primary/20' : ''}>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Badge variant={step === 2 ? 'default' : 'secondary'}>2</Badge>
                Input Definitions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {inputs.length > 0 && (
                <div className="space-y-2">
                  <Label>Defined Inputs</Label>
                  {inputs.map((input, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="font-medium">{input.name}</span>
                        <Badge variant="outline">{input.type}</Badge>
                        <Badge variant={input.required ? 'default' : 'secondary'}>
                          {input.required ? 'required' : 'optional'}
                        </Badge>
                        {input.default && (
                          <span className="text-sm text-muted-foreground">
                            default: {input.default}
                          </span>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeInput(index)}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              <div className="space-y-3 p-4 border rounded-lg">
                <Label>Add New Input</Label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label htmlFor="input-name">Name</Label>
                    <Input
                      id="input-name"
                      placeholder="input_name"
                      value={newInput.name}
                      onChange={(e) => setNewInput({ ...newInput, name: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="input-type">Type</Label>
                    <select
                      id="input-type"
                      className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors"
                      value={newInput.type}
                      onChange={(e) => setNewInput({ ...newInput, type: e.target.value as any })}
                    >
                      <option value="string">string</option>
                      <option value="number">number</option>
                      <option value="boolean">boolean</option>
                      <option value="array<string>">array&lt;string&gt;</option>
                      <option value="object">object</option>
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="input-required"
                      checked={newInput.required}
                      onChange={(e) => setNewInput({ ...newInput, required: e.target.checked })}
                    />
                    <Label htmlFor="input-required">Required</Label>
                  </div>
                  <div>
                    <Label htmlFor="input-default">Default Value</Label>
                    <Input
                      id="input-default"
                      placeholder="Optional default value"
                      value={newInput.default}
                      onChange={(e) => setNewInput({ ...newInput, default: e.target.value })}
                    />
                  </div>
                </div>
                <Button onClick={addInput} disabled={!newInput.name} size="sm">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Input
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {error && (
          <Card className="border-destructive bg-destructive/10">
            <CardContent className="pt-4">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        <DialogFooter className="flex justify-between">
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setStep(1)}
              disabled={step === 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              onClick={() => setStep(2)}
              disabled={!canProceedToStep2 || step === 2}
            >
              Next
            </Button>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={!canSave || loading}>
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating Prompt...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Create Prompt
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}