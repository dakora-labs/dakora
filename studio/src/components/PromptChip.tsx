import { X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export type ChipType = 'include' | 'variable';

interface PromptChipProps {
  type: ChipType;
  value: string;
  onDelete?: () => void;
  className?: string;
}

export function PromptChip({
  type,
  value,
  onDelete,
  className
}: PromptChipProps) {
  const isInclude = type === 'include';

  return (
    <Badge
      variant={isInclude ? 'default' : 'secondary'}
      className={cn(
        'inline-flex items-center gap-1 px-2 py-1 mx-0.5 my-0.5 select-none',
        'cursor-default font-mono text-xs',
        'group relative',
        isInclude && 'bg-blue-100 text-blue-700 border-blue-300 hover:bg-blue-200',
        !isInclude && 'bg-purple-100 text-purple-700 border-purple-300 hover:bg-purple-200',
        className
      )}
    >
      <span className="font-medium">
        {isInclude ? value.split('/').pop() : value}
      </span>

      {onDelete && (
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDelete();
          }}
          className="ml-1 hover:bg-black/10 rounded-full p-0.5 transition-colors"
          type="button"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </Badge>
  );
}