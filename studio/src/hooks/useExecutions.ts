import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import type { TimelineEvent } from '@/types';
import type { ExecutionDetailNew, ExecutionListFilters, ExecutionListItem, RelatedTracesResponse, TraceHierarchy } from '@/types';

interface UseExecutionsResult {
  executions: ExecutionListItem[];
  total: number;
  limit: number;
  offset: number;
  loading: boolean;
  error: string | null;
  refresh: () => void;
  setOffset: (nextOffset: number) => void;
}

export function useExecutions(filters: ExecutionListFilters = {}): UseExecutionsResult {
  const { api, projectId, contextLoading } = useAuthenticatedApi();
  const [executions, setExecutions] = useState<ExecutionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffsetState] = useState(filters.offset ?? 0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  const limit = filters.limit ?? 25;

  useEffect(() => {
    if (typeof filters.offset === 'number' && filters.offset !== offset) {
      setOffsetState(filters.offset);
    }
    if (filters.offset === undefined && offset !== 0) {
      setOffsetState(0);
    }
  }, [filters.offset, offset]);

  const effectiveFilters = useMemo<ExecutionListFilters>(() => {
    return {
      ...filters,
      limit,
      offset,
    };
  }, [filters, limit, offset]);

  useEffect(() => {
    if (!projectId || contextLoading) {
      return;
    }

    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.getExecutions(projectId, effectiveFilters);
        if (cancelled) {
          return;
        }
        const rows = Array.isArray(response.executions) ? response.executions : [];
        setExecutions(rows);
        const totalCount =
          typeof response.total === 'number' ? response.total : rows.length;
        setTotal(totalCount);
      } catch (err) {
        if (cancelled) {
          return;
        }
        console.error('Failed to load executions', err);
        setError(err instanceof Error ? err.message : 'Failed to load executions');
        setExecutions([]);
        setTotal(0);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [api, projectId, contextLoading, effectiveFilters, refreshIndex]);

  const setOffset = useCallback((nextOffset: number) => {
    setOffsetState(Math.max(0, nextOffset));
  }, []);

  const refresh = useCallback(() => {
    setRefreshIndex((index) => index + 1);
  }, []);

  return {
    executions,
    total,
    limit,
    offset,
    loading,
    error,
    refresh,
    setOffset,
  };
}

interface UseExecutionDetailResult {
  execution: ExecutionDetailNew | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
  refetchWithMessages: () => Promise<void>;
}

export function useExecutionDetail(traceId: string | undefined): UseExecutionDetailResult {
  const { api, projectId, contextLoading } = useAuthenticatedApi();
  const [execution, setExecution] = useState<ExecutionDetailNew | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeMessages, setIncludeMessages] = useState(false);

  const fetchExecution = useCallback(async (withMessages: boolean = false) => {
    if (!traceId || !projectId || contextLoading) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.getExecution(projectId, traceId, undefined, withMessages);
      setExecution(response);
      if (withMessages) {
        setIncludeMessages(true);
      }
    } catch (err) {
      console.error('Failed to load execution', err);
      setError(err instanceof Error ? err.message : 'Failed to load execution');
    } finally {
      setLoading(false);
    }
  }, [api, contextLoading, projectId, traceId]);

  const refetchWithMessages = useCallback(async () => {
    if (!includeMessages) {
      await fetchExecution(true);
    }
  }, [fetchExecution, includeMessages]);

  useEffect(() => {
    fetchExecution(false);
  }, [fetchExecution]);

  return {
    execution,
    loading,
    error,
    refresh: () => fetchExecution(includeMessages),
    refetchWithMessages,
  };
}

interface UseExecutionHierarchyResult {
  hierarchy: TraceHierarchy | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useExecutionHierarchy(traceId: string | undefined): UseExecutionHierarchyResult {
  const { api, projectId, contextLoading } = useAuthenticatedApi();
  const [hierarchy, setHierarchy] = useState<TraceHierarchy | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHierarchy = useCallback(async () => {
    if (!traceId || !projectId || contextLoading) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.getExecutionHierarchy(projectId, traceId);
      setHierarchy(response);
    } catch (err) {
      console.error('Failed to load execution hierarchy', err);
      setError(err instanceof Error ? err.message : 'Failed to load execution hierarchy');
    } finally {
      setLoading(false);
    }
  }, [api, contextLoading, projectId, traceId]);

  useEffect(() => {
    fetchHierarchy();
  }, [fetchHierarchy]);

  return {
    hierarchy,
    loading,
    error,
    refresh: fetchHierarchy,
  };
}

// New: Fetch normalized timeline for a trace
export function useExecutionTimeline(traceId: string | undefined): {
  timeline: TimelineEvent[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
} {
  const { api, projectId, contextLoading } = useAuthenticatedApi();
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTimeline = useCallback(async () => {
    if (!traceId || !projectId || contextLoading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getExecutionTimeline(projectId, traceId);
      setTimeline(Array.isArray(res?.events) ? res.events : []);
    } catch (err) {
      console.error('Failed to load timeline', err);
      setError(err instanceof Error ? err.message : 'Failed to load timeline');
      setTimeline([]);
    } finally {
      setLoading(false);
    }
  }, [api, projectId, traceId, contextLoading]);

  useEffect(() => {
    fetchTimeline();
  }, [fetchTimeline]);

  return { timeline, loading, error, refresh: fetchTimeline };
}

interface UseRelatedTracesResult {
  related: RelatedTracesResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useRelatedTraces(traceId: string | undefined): UseRelatedTracesResult {
  const { api, projectId, contextLoading } = useAuthenticatedApi();
  const [related, setRelated] = useState<RelatedTracesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRelated = useCallback(async () => {
    if (!traceId || !projectId || contextLoading) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.getRelatedTraces(projectId, traceId);
      setRelated(response);
    } catch (err) {
      console.error('Failed to load related traces', err);
      setError(err instanceof Error ? err.message : 'Failed to load related traces');
    } finally {
      setLoading(false);
    }
  }, [api, contextLoading, projectId, traceId]);

  useEffect(() => {
    fetchRelated();
  }, [fetchRelated]);

  return {
    related,
    loading,
    error,
    refresh: fetchRelated,
  };
}
