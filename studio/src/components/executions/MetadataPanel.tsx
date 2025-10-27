import { useMemo } from 'react';
import { Card } from '@/components/ui/card';

interface MetadataPanelProps {
  metadata: Record<string, unknown> | null;
}

export function MetadataPanel({ metadata }: MetadataPanelProps) {
  const hasMetadata = metadata && Object.keys(metadata).length > 0;
  const pretty = useMemo(() => {
    if (!hasMetadata) {
      return '{}';
    }
    return JSON.stringify(metadata, null, 2);
  }, [hasMetadata, metadata]);

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold">Metadata</h2>
        {!hasMetadata && (
          <span className="text-xs text-muted-foreground">No metadata provided</span>
        )}
      </div>
      <pre className="rounded-md bg-background border border-border/60 p-3 text-xs text-muted-foreground overflow-x-auto">
        {pretty}
      </pre>
    </Card>
  );
}
