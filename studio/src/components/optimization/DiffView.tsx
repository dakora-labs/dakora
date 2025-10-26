import { Card } from '@/components/ui/card';

interface DiffViewProps {
  original: string;
  optimized: string;
}

function computeSimpleDiff(original: string, optimized: string) {
  const originalWords = original.split(/(\s+)/);
  const optimizedWords = optimized.split(/(\s+)/);

  const result: Array<{ type: 'added' | 'removed' | 'unchanged'; value: string }> = [];
  let i = 0;
  let j = 0;

  while (i < originalWords.length || j < optimizedWords.length) {
    if (i >= originalWords.length) {
      result.push({ type: 'added', value: optimizedWords[j] });
      j++;
    } else if (j >= optimizedWords.length) {
      result.push({ type: 'removed', value: originalWords[i] });
      i++;
    } else if (originalWords[i] === optimizedWords[j]) {
      result.push({ type: 'unchanged', value: originalWords[i] });
      i++;
      j++;
    } else {
      const foundInOptimized = optimizedWords.indexOf(originalWords[i], j);
      const foundInOriginal = originalWords.indexOf(optimizedWords[j], i);

      if (foundInOptimized !== -1 && (foundInOriginal === -1 || foundInOptimized - j < foundInOriginal - i)) {
        result.push({ type: 'added', value: optimizedWords[j] });
        j++;
      } else if (foundInOriginal !== -1) {
        result.push({ type: 'removed', value: originalWords[i] });
        i++;
      } else {
        result.push({ type: 'removed', value: originalWords[i] });
        result.push({ type: 'added', value: optimizedWords[j] });
        i++;
        j++;
      }
    }
  }

  return result;
}

export function DiffView({ original, optimized }: DiffViewProps) {
  const diff = computeSimpleDiff(original, optimized);

  return (
    <Card className="p-4 bg-muted/20">
      <h4 className="text-sm font-medium mb-3 text-muted-foreground">
        Changes Highlighted
      </h4>
      <div className="text-sm font-mono whitespace-pre-wrap leading-relaxed">
        {diff.map((part, index) => {
          if (part.type === 'added') {
            return (
              <span
                key={index}
                className="bg-green-200/70 text-green-900 px-0.5 rounded"
              >
                {part.value}
              </span>
            );
          }
          if (part.type === 'removed') {
            return (
              <span
                key={index}
                className="bg-red-200/70 text-red-900 line-through px-0.5 rounded"
              >
                {part.value}
              </span>
            );
          }
          return (
            <span key={index} className="text-muted-foreground">
              {part.value}
            </span>
          );
        })}
      </div>
      <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-200 rounded" />
          <span>Added</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-200 rounded" />
          <span>Removed</span>
        </div>
      </div>
    </Card>
  );
}