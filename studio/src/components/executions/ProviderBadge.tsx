import { Badge } from '@/components/ui/badge';

const providerStyles: Record<string, string> = {
  azure_openai: 'bg-blue-100 text-blue-700 border-blue-200',
  openai: 'bg-emerald-100 text-emerald-700 border-emerald-200',
};

interface ProviderBadgeProps {
  provider: string | null | undefined;
}

export function ProviderBadge({ provider }: ProviderBadgeProps) {
  const normalized = provider?.toLowerCase() ?? 'unknown';
  const className =
    providerStyles[normalized] ?? 'bg-muted text-muted-foreground border-muted/60';

  return (
    <Badge
      variant="outline"
      className={`text-xs font-medium border ${className}`}
    >
      {provider ?? 'unknown'}
    </Badge>
  );
}
