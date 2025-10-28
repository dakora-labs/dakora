import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Plus, Trash2, Copy, Check, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useApiKeys, useCreateApiKey, useDeleteApiKey } from '@/hooks/useApi';
import type { ApiKey } from '@/types';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import { useToast } from '@/hooks/use-toast';

export function SettingsPage() {
  const { projectSlug } = useParams<{ projectSlug: string }>();
  const { projectId, userContext, api } = useAuthenticatedApi();
  const { apiKeys, loading, error, refetch } = useApiKeys(projectId);
  const { createApiKey, loading: creating, error: createError } = useCreateApiKey(projectId);
  const { deleteApiKey, loading: deleting } = useDeleteApiKey(projectId);
  const { toast } = useToast();

  const [showNewKeyDialog, setShowNewKeyDialog] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyExpiration, setNewKeyExpiration] = useState<string | null>(null);
  const [createdKey, setCreatedKey] = useState<{ key: string; name: string | null } | null>(null);
  const [keyToCopy, setKeyToCopy] = useState<string | null>(null);
  const [keyToDelete, setKeyToDelete] = useState<ApiKey | null>(null);

  const [budgetUsd, setBudgetUsd] = useState<string>('');
  const [alertThreshold, setAlertThreshold] = useState<number>(80);
  const [enforcementMode, setEnforcementMode] = useState<string>('strict');
  const [savingBudget, setSavingBudget] = useState(false);
  const [budgetLoading, setBudgetLoading] = useState(true);

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) {
      return;
    }

    try {
      const response = await createApiKey({
        name: newKeyName.trim(),
        expires_in_days: newKeyExpiration ? parseInt(newKeyExpiration) : null,
      });

      setCreatedKey({ key: response.key, name: response.name });
      setShowNewKeyDialog(false);
      setNewKeyName('');
      setNewKeyExpiration(null);
      refetch();
    } catch (err) {
      console.error('Failed to create API key:', err);
    }
  };

  const handleDeleteKey = async () => {
    if (!keyToDelete) return;

    try {
      await deleteApiKey(keyToDelete.id);
      refetch();
      setKeyToDelete(null);
    } catch (err) {
      console.error('Failed to delete API key:', err);
    }
  };

  const handleCopyKey = async (key: string) => {
    await navigator.clipboard.writeText(key);
    setKeyToCopy(key);
    setTimeout(() => setKeyToCopy(null), 2000);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatExpiration = (expiresAt: string | null) => {
    if (!expiresAt) return 'Never';
    return formatDate(expiresAt);
  };

  useEffect(() => {
    if (!projectId) return;

    const loadBudget = async () => {
      try {
        setBudgetLoading(true);
        const budget = await api.getBudget(projectId);

        if (budget.budget_usd !== null) {
          setBudgetUsd(budget.budget_usd.toString());
        }
        setAlertThreshold(budget.alert_threshold_pct || 80);
        setEnforcementMode(budget.enforcement_mode || 'strict');
      } catch (error) {
        console.error('Failed to load budget:', error);
      } finally {
        setBudgetLoading(false);
      }
    };

    loadBudget();
  }, [projectId, api]);

  const handleSaveBudget = async () => {
    if (!projectId) return;

    setSavingBudget(true);
    try {
      await api.updateBudget(projectId, {
        budget_monthly_usd: budgetUsd ? parseFloat(budgetUsd) : null,
        alert_threshold_pct: alertThreshold,
        enforcement_mode: enforcementMode,
      });

      toast({
        title: 'Budget Settings Saved',
        description: 'Your budget configuration has been updated successfully.',
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save budget settings';
      toast({
        title: 'Error Saving Budget',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setSavingBudget(false);
    }
  };

  const getEnforcementModeDescription = () => {
    switch (enforcementMode) {
      case 'strict':
        return 'Agent executions will be blocked when budget is exceeded';
      case 'alert':
        return 'Warnings logged but executions allowed';
      case 'off':
        return 'Budget tracked but not enforced';
      default:
        return '';
    }
  };


  return (
    <div className="h-full overflow-auto bg-background">
      <div className="max-w-5xl mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold mb-1">Project Settings</h1>
          <p className="text-sm text-muted-foreground">
            Configure project identity, API keys, and other controls.
          </p>
        </div>

        <Card className="p-5 mb-4">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-semibold mb-0.5">Project Name</h2>
              <p className="text-sm text-muted-foreground">
                {userContext?.project_name || projectSlug || 'Loading...'}
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-5 mb-4">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold mb-0.5">API Keys</h2>
              <p className="text-xs text-muted-foreground">
                Manage API keys for this project. You have used {apiKeys?.count || 0} of {apiKeys?.limit || 4} keys.
              </p>
            </div>
            <Button
              onClick={() => setShowNewKeyDialog(true)}
              disabled={loading || !!(apiKeys && apiKeys.count >= apiKeys.limit)}
              size="sm"
            >
              <Plus className="w-4 h-4 mr-2" />
              New Key
            </Button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {loading && (
            <div className="text-center py-8 text-muted-foreground">Loading API keys...</div>
          )}

          {!loading && apiKeys && apiKeys.keys.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              No API keys yet. Create one to get started.
            </div>
          )}

          {!loading && apiKeys && apiKeys.keys.length > 0 && (
            <div className="space-y-2">
              {apiKeys.keys.map((key) => (
                <div
                  key={key.id}
                  className="flex items-center justify-between p-3 border border-border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <code className="text-xs font-mono">{key.key_preview}</code>
                      {key.name && (
                        <span className="text-xs text-muted-foreground">({key.name})</span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                      <span>Created {formatDate(key.created_at)}</span>
                      <span>Expires {formatExpiration(key.expires_at)}</span>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setKeyToDelete(key)}
                    disabled={deleting}
                    className="h-9 w-9"
                  >
                    <Trash2 className="w-4 h-4 text-destructive" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-5">
          <div className="mb-4">
            <h2 className="text-lg font-semibold mb-0.5">Budget Controls</h2>
            <p className="text-xs text-muted-foreground">
              Set monthly spending limits to prevent cost overruns
            </p>
          </div>

          {budgetLoading ? (
            <div className="text-center py-8 text-muted-foreground">Loading budget settings...</div>
          ) : (
            <div className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="budget">Monthly Budget (USD)</Label>
                <Input
                  id="budget"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="No limit"
                  value={budgetUsd}
                  onChange={(e) => setBudgetUsd(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Leave empty for unlimited spending
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="enforcement-mode">Enforcement Mode</Label>
                <Select value={enforcementMode} onValueChange={setEnforcementMode}>
                  <SelectTrigger id="enforcement-mode">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="strict">Strict - Block executions when exceeded</SelectItem>
                    <SelectItem value="alert">Alert - Log warnings but allow executions</SelectItem>
                    <SelectItem value="off">Off - Track only, no enforcement</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {getEnforcementModeDescription()}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="alert-threshold">
                  Warning Threshold: {alertThreshold}%
                </Label>
                <Slider
                  id="alert-threshold"
                  min={50}
                  max={100}
                  step={5}
                  value={[alertThreshold]}
                  onValueChange={(value) => setAlertThreshold(value[0])}
                  className="py-2"
                />
                <p className="text-xs text-muted-foreground">
                  Show warning when budget reaches this percentage
                </p>
              </div>

              <Button onClick={handleSaveBudget} disabled={savingBudget}>
                {savingBudget ? 'Saving...' : 'Save Budget Settings'}
              </Button>
            </div>
          )}
        </Card>

        <Dialog open={showNewKeyDialog} onOpenChange={setShowNewKeyDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New API Key</DialogTitle>
              <DialogDescription>
                Generate a new API key for this project. The full key will only be shown once.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="key-name">Name</Label>
                <Input
                  id="key-name"
                  placeholder="My API Key"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="key-expiration">Expiration</Label>
                <Select
                  value={newKeyExpiration || 'never'}
                  onValueChange={(value) => setNewKeyExpiration(value === 'never' ? null : value)}
                >
                  <SelectTrigger id="key-expiration">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="30">30 days</SelectItem>
                    <SelectItem value="90">90 days</SelectItem>
                    <SelectItem value="365">1 year</SelectItem>
                    <SelectItem value="never">Never</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {createError && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-2 text-sm text-destructive">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {createError}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setShowNewKeyDialog(false);
                  setNewKeyName('');
                  setNewKeyExpiration(null);
                }}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button onClick={handleCreateKey} disabled={creating || !newKeyName.trim()}>
                {creating ? 'Creating...' : 'Create Key'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={!!createdKey} onOpenChange={() => setCreatedKey(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>API Key Created</DialogTitle>
              <DialogDescription>
                Save this key now. You won't be able to see it again.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {createdKey?.name && (
                <div>
                  <Label>Name</Label>
                  <p className="text-sm text-muted-foreground">{createdKey.name}</p>
                </div>
              )}

              <div className="space-y-2">
                <Label>API Key</Label>
                <div className="flex gap-2">
                  <Input
                    value={createdKey?.key || ''}
                    readOnly
                    className="font-mono text-sm"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => createdKey && handleCopyKey(createdKey.key)}
                  >
                    {keyToCopy === createdKey?.key ? (
                      <Check className="w-4 h-4 text-green-600" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button onClick={() => setCreatedKey(null)}>Done</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <AlertDialog open={!!keyToDelete} onOpenChange={() => setKeyToDelete(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete API Key?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. The API key will immediately stop working.
                {keyToDelete?.name && (
                  <>
                    <br />
                    <br />
                    <strong>Key: {keyToDelete.name}</strong>
                  </>
                )}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteKey}
                disabled={deleting}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}