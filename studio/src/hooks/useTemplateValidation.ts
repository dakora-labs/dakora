import { useEffect, useMemo, useRef, useState } from 'react';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import { useToast } from '@/hooks/use-toast';
import type { ValidateTemplateResponse } from '@/types';
import type { EditorMarker } from '@/components/RichTemplateEditor';

function toMarkers(template: string, validation: ValidateTemplateResponse | null): EditorMarker[] {
  if (!validation) return [];

  const markers: EditorMarker[] = [];

  // Syntax/include errors
  for (const err of validation.errors) {
    const line = err.line ?? 1;
    const col = err.column ?? 1;
    markers.push({
      message: err.message,
      severity: 'error',
      startLineNumber: Math.max(1, line),
      startColumn: Math.max(1, col),
      endLineNumber: Math.max(1, line),
      endColumn: Math.max(1, col + 1),
    });
  }

  // Highlight missing variables at each usage within {{ ... }}
  const text = template;
  const lineOffsets: number[] = [];
  {
    let acc = 0;
    for (const line of text.split('\n')) {
      lineOffsets.push(acc);
      acc += line.length + 1; // account for newline
    }
  }

  function indexToPos(index: number): { line: number; col: number } {
    // binary search could be added but linear is fine for typical sizes
    let line = 0;
    for (let i = 0; i < lineOffsets.length; i++) {
      if (i + 1 === lineOffsets.length || index < lineOffsets[i + 1]) {
        line = i;
        break;
      }
    }
    const col = index - lineOffsets[line] + 1; // 1-based
    return { line: line + 1, col };
  }

  const missing = new Set(validation.variables_missing || []);
  if (missing.size > 0) {
    for (const name of missing) {
      // Match occurrences within mustache blocks
      const pattern = new RegExp(String.raw`\{\{[^\}]*\b${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\b[^\}]*\}\}`, 'g');
      let match: RegExpExecArray | null;
      while ((match = pattern.exec(text)) !== null) {
        // Find the variable name position within the match
        const inner = match[0];
        const innerIdx = inner.search(new RegExp(String.raw`\b${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\b`));
        const startIndex = (match.index ?? 0) + (innerIdx >= 0 ? innerIdx : 0) + 0;
        const { line, col } = indexToPos(startIndex);
        markers.push({
          message: `Variable '${name}' is not declared`,
          severity: 'warning',
          startLineNumber: line,
          startColumn: col,
          endLineNumber: line,
          endColumn: col + name.length,
        });
      }
    }
  }

  return markers;
}

export function useTemplateValidation(template: string, declaredVariables: string[] | undefined) {
  const { api, projectId } = useAuthenticatedApi();
  const { toast } = useToast();
  const [validation, setValidation] = useState<ValidateTemplateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latestRequestRef = useRef(0);
  const declaredKey = JSON.stringify(declaredVariables ?? []);
  const lastToastErrorRef = useRef<string | null>(null);

  useEffect(() => {
    if (!projectId) {
      setValidation(null);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const requestId = ++latestRequestRef.current;
    const handle = setTimeout(async () => {
      try {
        setLoading(true);
        setError(null);
        const resp = await api.validateTemplate(
          projectId,
          {
            template,
            declared_variables: declaredVariables ?? null,
          },
          { signal: controller.signal }
        );
        if (latestRequestRef.current !== requestId) {
          return;
        }
        setValidation(resp);
      } catch (e: any) {
        if (controller.signal.aborted || latestRequestRef.current !== requestId) {
          return;
        }
        if (e?.name === 'AbortError') {
          return;
        }
        setError(e?.message ?? 'Validation failed');
      } finally {
        if (latestRequestRef.current === requestId) {
          setLoading(false);
        }
      }
    }, 400); // debounce

    return () => {
      controller.abort();
      clearTimeout(handle);
    };
  }, [template, declaredKey, api, projectId]);

  useEffect(() => {
    if (error && lastToastErrorRef.current !== error) {
      toast({
        variant: 'destructive',
        title: 'Template validation failed',
        description: error,
      });
      lastToastErrorRef.current = error;
    }

    if (!error) {
      lastToastErrorRef.current = null;
    }
  }, [error, toast]);

  const markers = useMemo(() => toMarkers(template, validation), [template, validation]);

  return { validation, markers, loading, error };
}
