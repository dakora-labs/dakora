import { useState, useEffect } from 'react';
import { History, RotateCcw, Clock, AlertCircle, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import type { VersionHistoryItem, Template } from '@/types';

interface VersionHistorySheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  promptId: string;
  currentVersion: string;
  onRestore: (version: number) => Promise<void>;
  getVersionHistory: (projectId: string, promptId: string) => Promise<{ versions: VersionHistoryItem[]; total: number }>;
  getPromptVersion: (projectId: string, promptId: string, version: number) => Promise<Template>;
}

export function VersionHistorySheet({
  open,
  onOpenChange,
  projectId,
  promptId,
  currentVersion,
  onRestore,
  getVersionHistory,
  getPromptVersion,
}: VersionHistorySheetProps) {
  const [versions, setVersions] = useState<VersionHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [viewingVersion, setViewingVersion] = useState<Template | null>(null);
  const [viewingVersionNumber, setViewingVersionNumber] = useState<number | null>(null);
  const [loadingVersion, setLoadingVersion] = useState(false);
  const [showViewDialog, setShowViewDialog] = useState(false);

  useEffect(() => {
    if (open && projectId && promptId) {
      loadVersions();
    }
  }, [open, projectId, promptId]);

  const loadVersions = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await getVersionHistory(projectId, promptId);
      setVersions(response.versions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load version history');
    } finally {
      setLoading(false);
    }
  };

  const handleRestoreClick = (version: number) => {
    setSelectedVersion(version);
    setShowConfirmDialog(true);
  };

  const handleViewClick = async (version: number) => {
    try {
      setLoadingVersion(true);
      setError('');
      const versionData = await getPromptVersion(projectId, promptId, version);
      setViewingVersion(versionData);
      setViewingVersionNumber(version);
      setShowViewDialog(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load version content');
    } finally {
      setLoadingVersion(false);
    }
  };

  const handleConfirmRestore = async () => {
    if (selectedVersion === null) return;

    try {
      setRestoring(true);
      setError('');
      await onRestore(selectedVersion);
      setShowConfirmDialog(false);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restore version');
    } finally {
      setRestoring(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  };

  const formatFullDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short'
    });
  };

  return (
    <TooltipProvider delayDuration={100}>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl h-[85vh] flex flex-col gap-0 p-0">
          <div className="p-6 pb-4 border-b">
            <DialogHeader>
              <div className="flex items-center gap-2">
                <History className="w-5 h-5 text-muted-foreground" />
                <DialogTitle>Version History</DialogTitle>
              </div>
              <DialogDescription>
                View and restore previous versions of this prompt
              </DialogDescription>
            </DialogHeader>

            {error && (
              <div className="bg-destructive/10 border border-destructive/20 rounded-md px-3 py-2 flex items-start gap-2 mt-4">
                <AlertCircle className="w-4 h-4 text-destructive mt-0.5" />
                <p className="text-sm text-destructive">{error}</p>
              </div>
            )}
          </div>

          <div className="flex-1 overflow-auto px-6 py-4">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <p className="text-sm text-muted-foreground">Loading versions...</p>
              </div>
            ) : versions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 gap-2">
                <History className="w-12 h-12 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">No version history available</p>
              </div>
            ) : (
              <div className="space-y-3">
                {versions.map((version, index) => {
                  const isCurrentVersion = version.version.toString() === currentVersion;
                  const isLatest = index === 0;

                  return (
                    <div key={version.version} className="relative">
                      <div className={`rounded-lg border p-4 transition-colors hover:border-muted-foreground/20 ${
                        isCurrentVersion ? 'border-primary bg-primary/5' : 'border-border bg-card'
                      }`}>
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge variant={isCurrentVersion ? 'default' : 'secondary'} className="font-mono">
                                v{version.version}
                              </Badge>
                              {isLatest && !isCurrentVersion && (
                                <Badge variant="outline" className="text-xs">
                                  Latest
                                </Badge>
                              )}
                              {isCurrentVersion && (
                                <Badge variant="default" className="text-xs">
                                  Current
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <Clock className="w-3 h-3" />
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="cursor-help">
                                    {formatDate(version.created_at)}
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>{formatFullDate(version.created_at)}</p>
                                </TooltipContent>
                              </Tooltip>
                              {version.created_by && (
                                <>
                                  <span>•</span>
                                  <span className="truncate">{version.created_by}</span>
                                </>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleViewClick(version.version)}
                              disabled={loadingVersion}
                              className="gap-2"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              View
                            </Button>
                            {!isCurrentVersion && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleRestoreClick(version.version)}
                                className="gap-2"
                              >
                                <RotateCcw className="w-3.5 h-3.5" />
                                Restore
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                      {index < versions.length - 1 && (
                        <div className="absolute left-[22px] top-full w-px h-3 bg-border" />
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restore version {selectedVersion}?</AlertDialogTitle>
            <AlertDialogDescription>
              This will create a new version with the content from v{selectedVersion}. Your current version will be preserved in the history.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={restoring}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmRestore} disabled={restoring}>
              {restoring ? 'Restoring...' : 'Restore'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={showViewDialog} onOpenChange={setShowViewDialog}>
        <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <Eye className="w-5 h-5 text-muted-foreground" />
              <DialogTitle>
                View Version {viewingVersionNumber}
              </DialogTitle>
            </div>
            <DialogDescription>
              Read-only preview of this version's template content
            </DialogDescription>
          </DialogHeader>

          {viewingVersion && (
            <ScrollArea className="flex-1 -mx-6 px-6">
              <div className="space-y-4 py-4">
                {viewingVersion.description && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium">Description</h3>
                    <p className="text-sm text-muted-foreground">{viewingVersion.description}</p>
                  </div>
                )}

                <div className="space-y-2">
                  <h3 className="text-sm font-medium">Template</h3>
                  <div className="border rounded-md">
                    <Textarea
                      value={viewingVersion.template}
                      readOnly
                      className="min-h-[300px] font-mono text-sm resize-none border-0 focus-visible:ring-0"
                    />
                  </div>
                </div>

                {viewingVersion.inputs && Object.keys(viewingVersion.inputs).length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium">Variables</h3>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(viewingVersion.inputs).map(([name, spec]) => (
                        <Badge key={name} variant="secondary" className="gap-1.5 text-xs">
                          <span>{name}</span>
                          <span className="text-muted-foreground">({spec.type})</span>
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          )}
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  );
}