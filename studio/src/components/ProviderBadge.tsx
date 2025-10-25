import { Badge } from '@/components/ui/badge';
import { Cloud, Sparkles } from 'lucide-react';

interface ProviderBadgeProps {
  provider: string;
  size?: 'sm' | 'md';
  showIcon?: boolean;
}

const providerConfig: Record<string, { label: string; color: string; icon: typeof Cloud }> = {
  'azure_openai': {
    label: 'Azure',
    color: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
    icon: Cloud,
  },
  'google_gemini': {
    label: 'Gemini',
    color: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20',
    icon: Sparkles,
  },
};

export function ProviderBadge({ provider, size = 'sm', showIcon = true }: ProviderBadgeProps) {
  const config = providerConfig[provider] || {
    label: provider,
    color: 'bg-gray-500/10 text-gray-600 border-gray-500/20',
    icon: Cloud,
  };

  const Icon = config.icon;
  const sizeClasses = size === 'sm' ? 'h-5 text-xs px-1.5' : 'h-6 text-sm px-2';

  return (
    <Badge variant="outline" className={`${config.color} ${sizeClasses} font-medium gap-1`}>
      {showIcon && <Icon className="w-3 h-3" />}
      <span>{config.label}</span>
    </Badge>
  );
}