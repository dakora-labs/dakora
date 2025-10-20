import { useState, useEffect } from 'react';
import { Activity, AlertCircle, CheckCircle, Wifi, WifiOff, Server, Database, Folder, Cloud } from 'lucide-react';
import { api } from '../utils/api';
import { Badge } from '@/components/ui/badge';
import type { HealthResponse } from '../types';

export function StatusBar() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const healthData = await api.getHealth();
        setHealth(healthData);
        setConnected(true);
      } catch (error) {
        console.error('Health check failed:', error);
        setConnected(false);
        setHealth(null);
      } finally {
        setLoading(false);
      }
    };

    // Initial check
    checkHealth();

    // Check every 30 seconds
    const interval = setInterval(checkHealth, 30000);

    return () => clearInterval(interval);
  }, []);

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

          {/* Template Count */}
          {health && (
            <Badge variant="outline" className="text-xs">
              {health.templates_loaded} template{health.templates_loaded !== 1 ? 's' : ''}
            </Badge>
          )}
        </div>

        <div className="flex items-center flex-wrap gap-3 text-xs">
          {/* Prompt Directory or Cloud Location */}
          {health?.vault_config && (
            <div className="flex items-center gap-1">
              {health.vault_config.registry_type === 'azure' ? (
                <>
                  <Cloud className="w-3 h-3" />
                  <span className="hidden sm:inline">Cloud:</span>
                  <code className="text-xs bg-muted px-1 py-0.5 rounded">
                    {health.vault_config.cloud_location}
                  </code>
                </>
              ) : (
                <>
                  <Folder className="w-3 h-3" />
                  <span className="hidden sm:inline">Dir:</span>
                  <code className="text-xs bg-muted px-1 py-0.5 rounded">
                    {health.vault_config.prompt_dir}
                  </code>
                </>
              )}
            </div>
          )}

          {/* Logging Status */}
          {health?.vault_config && (
            <div className="flex items-center gap-1">
              <Database className="w-3 h-3" />
              <span className="hidden sm:inline">Log:</span>
              <Badge
                variant={health.vault_config.logging_enabled ? "secondary" : "outline"}
                className="text-xs"
              >
                {health.vault_config.logging_enabled ? 'enabled' : 'disabled'}
              </Badge>
            </div>
          )}

          {/* Version */}
          <span className="text-muted-foreground/70">Dakora</span>
        </div>
      </div>
    </div>
  );
}