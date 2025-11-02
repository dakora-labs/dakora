import { useState, useEffect } from 'react';
import { Activity, AlertCircle, CheckCircle, Wifi, WifiOff, Server, Folder, MessageSquare, Bug } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { BugReportDialog } from '@/components/BugReportDialog';
import type { HealthResponse } from '../types';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import { useFeedbackContext } from '@/contexts/FeedbackContext';
import { useUserContext } from '@/contexts/UserContext';

export function StatusBar() {
  const { api, projectId } = useAuthenticatedApi();
  const { openFeedbackDialog } = useFeedbackContext();
  const { userContext } = useUserContext();
  const [bugReportOpen, setBugReportOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [promptCount, setPromptCount] = useState<number>(0);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkHealthAndStats = async () => {
      try {
        // Fetch health data
        const healthData = await api.getHealth();
        setHealth(healthData);

        // Fetch project stats if we have a project ID
        if (projectId) {
          const statsData = await api.getProjectStats(projectId);
          setPromptCount(statsData.prompts_count);
        }

        setConnected(true);
      } catch (error) {
        console.error('Health/stats check failed:', error);
        setConnected(false);
        setHealth(null);
      } finally {
        setLoading(false);
      }
    };

    // Initial check
    checkHealthAndStats();

    // Check every 30 seconds
    const interval = setInterval(checkHealthAndStats, 30000);

    return () => clearInterval(interval);
  }, [projectId, api]);

  if (loading) {
    return (
      <div className="bg-muted/30 border-t border-border px-4 py-2 text-xs text-muted-foreground flex items-center justify-between">
        <div className="flex items-center">
          <Activity className="w-3 h-3 mr-2 animate-pulse" />
          Connecting...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-muted/30 border-t border-border px-4 py-2 text-xs text-muted-foreground">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex items-center flex-wrap gap-3">
          {/* Connection Status */}
          <div className="flex items-center gap-1">
            {connected ? (
              <>
                <Wifi className="w-3 h-3 text-green-500" />
                <span className="text-green-600 font-medium">Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3 text-destructive" />
                <span className="text-destructive font-medium">Disconnected</span>
              </>
            )}
          </div>

          {/* Health Status */}
          {health && (
            <div className="flex items-center gap-1">
              {health.status === 'healthy' ? (
                <>
                  <CheckCircle className="w-3 h-3 text-green-500" />
                  <Badge variant="secondary" className="text-xs bg-green-100 text-green-700 border-green-200">
                    <Server className="w-3 h-3 mr-1" />
                    Healthy
                  </Badge>
                </>
              ) : (
                <>
                  <AlertCircle className="w-3 h-3 text-destructive" />
                  <Badge variant="destructive" className="text-xs">
                    <Server className="w-3 h-3 mr-1" />
                    Issues
                  </Badge>
                </>
              )}
            </div>
          )}

          {/* Prompt Count */}
          {connected && (
            <Badge variant="outline" className="text-xs">
              {promptCount} prompt{promptCount !== 1 ? 's' : ''}
            </Badge>
          )}
        </div>

        <div className="flex items-center flex-wrap gap-3 text-xs">
          {/* Prompt Directory (Local Mode Only) */}
          {health?.vault_config && health.vault_config.registry_type === 'local' && (
            <div className="flex items-center gap-1">
              <Folder className="w-3 h-3" />
              <span className="hidden sm:inline">Dir:</span>
              <code className="text-xs bg-muted px-1 py-0.5 rounded">
                {health.vault_config.prompt_dir}
              </code>
            </div>
          )}

          {/* Bug Report Button */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={() => setBugReportOpen(true)}
                >
                  <Bug className="w-3 h-3 mr-1" />
                  <span className="hidden sm:inline">Report Bug</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Report an issue or bug</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {/* Feedback Button */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={openFeedbackDialog}
                >
                  <MessageSquare className="w-3 h-3 mr-1" />
                  <span className="hidden sm:inline">Feedback</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Give feedback about Dakora</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {/* Version */}
          <span className="text-muted-foreground/70">Dakora</span>
        </div>
      </div>

      <BugReportDialog
        open={bugReportOpen}
        onOpenChange={setBugReportOpen}
        userEmail={userContext?.email}
      />
    </div>
  );
}