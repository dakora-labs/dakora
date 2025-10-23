import { useState, useEffect, useCallback, useMemo } from 'react';
import { api, ApiError, createApiClient } from '../utils/api';
import type { Template, PartListResponse, PromptPart, CreatePartRequest, UpdatePartRequest, ApiKeyListResponse, ApiKeyCreateRequest, ApiKeyCreateResponse } from '../types';
import { useAuthToken } from '@/utils/auth';

export function usePrompts(projectId: string | undefined) {
  const [prompts, setPrompts] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPrompts = useCallback(async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await api.getPrompts(projectId);
      setPrompts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch prompts');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchPrompts();
  }, [fetchPrompts]);

  return { prompts, loading, error, refetch: fetchPrompts };
}

export function usePrompt(projectId: string | undefined, id: string | null) {
  const [prompt, setPrompt] = useState<Template | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPrompt = useCallback(async (promptId: string) => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await api.getPrompt(projectId, promptId);
      setPrompt(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch prompt');
      setPrompt(null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (id) {
      fetchPrompt(id);
    } else {
      setPrompt(null);
      setError(null);
    }
  }, [id, fetchPrompt]);

  return { prompt, loading, error, refetch: id ? () => fetchPrompt(id) : undefined };
}

export function useExamples() {
  const [examples, setExamples] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchExamples() {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getExamples();
        setExamples(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch examples');
      } finally {
        setLoading(false);
      }
    }

    fetchExamples();
  }, []);

  return { examples, loading, error };
}

export function useRender(projectId: string | undefined) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const render = useCallback(async (promptId: string, inputs: Record<string, unknown>) => {
    if (!projectId) {
      throw new Error('Project ID is required');
    }

    try {
      setLoading(true);
      setError(null);
      const response = await api.renderPrompt(projectId, promptId, { inputs });
      return response;
    } catch (err) {
      const errorMessage = err instanceof ApiError
        ? err.message
        : err instanceof Error
        ? err.message
        : 'Failed to render prompt';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  return { render, loading, error, clearError: () => setError(null) };
}

export function useCreatePrompt(projectId: string | undefined) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createPrompt = useCallback(async (template: Omit<Template, 'inputs'> & {
    inputs: Record<string, { type: string; required: boolean; default?: unknown }>
  }) => {
    if (!projectId) {
      throw new Error('Project ID is required');
    }

    try {
      setLoading(true);
      setError(null);
      const response = await api.createPrompt(projectId, template);
      return response;
    } catch (err) {
      const errorMessage = err instanceof ApiError
        ? err.message
        : err instanceof Error
        ? err.message
        : 'Failed to create prompt';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  return { createPrompt, loading, error, clearError: () => setError(null) };
}

export function useUpdatePrompt(projectId: string | undefined) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updatePrompt = useCallback(async (id: string, template: Partial<Omit<Template, 'id' | 'inputs'>> & {
    inputs?: Record<string, { type: string; required: boolean; default?: unknown }>
  }) => {
    if (!projectId) {
      throw new Error('Project ID is required');
    }

    try {
      setLoading(true);
      setError(null);
      const response = await api.updatePrompt(projectId, id, template);
      return response;
    } catch (err) {
      const errorMessage = err instanceof ApiError
        ? err.message
        : err instanceof Error
        ? err.message
        : 'Failed to update prompt';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  return { updatePrompt, loading, error, clearError: () => setError(null) };
}

export function usePromptParts(projectId: string | undefined) {
  const { getToken } = useAuthToken();
  const authenticatedApi = useMemo(() => createApiClient(getToken), [getToken]);

  const [parts, setParts] = useState<PartListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchParts = useCallback(async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await authenticatedApi.getPromptParts(projectId);
      setParts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch prompt parts');
    } finally {
      setLoading(false);
    }
  }, [projectId, authenticatedApi]);

  useEffect(() => {
    fetchParts();
  }, [fetchParts]);

  return { parts, loading, error, refetch: fetchParts };
}

export function usePromptPart(projectId: string | undefined, partId: string | null) {
  const { getToken } = useAuthToken();
  const authenticatedApi = useMemo(() => createApiClient(getToken), [getToken]);

  const [part, setPart] = useState<PromptPart | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPart = useCallback(async (id: string) => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await authenticatedApi.getPromptPart(projectId, id);
      setPart(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch prompt part');
      setPart(null);
    } finally {
      setLoading(false);
    }
  }, [projectId, authenticatedApi]);

  useEffect(() => {
    if (partId) {
      fetchPart(partId);
    } else {
      setPart(null);
      setError(null);
    }
  }, [partId, fetchPart]);

  return { part, loading, error, refetch: partId ? () => fetchPart(partId) : undefined };
}

export function useCreatePromptPart(projectId: string | undefined) {
  const { getToken } = useAuthToken();
  const authenticatedApi = useMemo(() => createApiClient(getToken), [getToken]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createPart = useCallback(async (part: CreatePartRequest) => {
    if (!projectId) {
      throw new Error('Project ID is required');
    }

    try {
      setLoading(true);
      setError(null);
      const response = await authenticatedApi.createPromptPart(projectId, part);
      return response;
    } catch (err) {
      const errorMessage = err instanceof ApiError
        ? err.message
        : err instanceof Error
        ? err.message
        : 'Failed to create prompt part';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, authenticatedApi]);

  return { createPart, loading, error, clearError: () => setError(null) };
}

export function useUpdatePromptPart(projectId: string | undefined) {
  const { getToken } = useAuthToken();
  const authenticatedApi = useMemo(() => createApiClient(getToken), [getToken]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updatePart = useCallback(async (partId: string, part: UpdatePartRequest) => {
    if (!projectId) {
      throw new Error('Project ID is required');
    }

    try {
      setLoading(true);
      setError(null);
      const response = await authenticatedApi.updatePromptPart(projectId, partId, part);
      return response;
    } catch (err) {
      const errorMessage = err instanceof ApiError
        ? err.message
        : err instanceof Error
        ? err.message
        : 'Failed to update prompt part';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, authenticatedApi]);

  return { updatePart, loading, error, clearError: () => setError(null) };
}

export function useDeletePromptPart(projectId: string | undefined) {
  const { getToken } = useAuthToken();
  const authenticatedApi = useMemo(() => createApiClient(getToken), [getToken]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const deletePart = useCallback(async (partId: string) => {
    if (!projectId) {
      throw new Error('Project ID is required');
    }

    try {
      setLoading(true);
      setError(null);
      await authenticatedApi.deletePromptPart(projectId, partId);
    } catch (err) {
      const errorMessage = err instanceof ApiError
        ? err.message
        : err instanceof Error
        ? err.message
        : 'Failed to delete prompt part';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, authenticatedApi]);

  return { deletePart, loading, error, clearError: () => setError(null) };
}

export function useApiKeys(projectId: string | undefined) {
  const { getToken } = useAuthToken();
  const authenticatedApi = useMemo(() => createApiClient(getToken), [getToken]);

  const [apiKeys, setApiKeys] = useState<ApiKeyListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchApiKeys = useCallback(async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await authenticatedApi.getApiKeys(projectId);
      setApiKeys(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch API keys');
    } finally {
      setLoading(false);
    }
  }, [projectId, authenticatedApi]);

  useEffect(() => {
    fetchApiKeys();
  }, [fetchApiKeys]);

  return { apiKeys, loading, error, refetch: fetchApiKeys };
}

export function useCreateApiKey(projectId: string | undefined) {
  const { getToken } = useAuthToken();
  const authenticatedApi = useMemo(() => createApiClient(getToken), [getToken]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createApiKey = useCallback(async (request: ApiKeyCreateRequest): Promise<ApiKeyCreateResponse> => {
    if (!projectId) {
      throw new Error('Project ID is required');
    }

    try {
      setLoading(true);
      setError(null);
      const response = await authenticatedApi.createApiKey(projectId, request);
      return response;
    } catch (err) {
      const errorMessage = err instanceof ApiError
        ? err.message
        : err instanceof Error
        ? err.message
        : 'Failed to create API key';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, authenticatedApi]);

  return { createApiKey, loading, error, clearError: () => setError(null) };
}

export function useDeleteApiKey(projectId: string | undefined) {
  const { getToken } = useAuthToken();
  const authenticatedApi = useMemo(() => createApiClient(getToken), [getToken]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const deleteApiKey = useCallback(async (keyId: string): Promise<void> => {
    if (!projectId) {
      throw new Error('Project ID is required');
    }

    try {
      setLoading(true);
      setError(null);
      await authenticatedApi.deleteApiKey(projectId, keyId);
    } catch (err) {
      const errorMessage = err instanceof ApiError
        ? err.message
        : err instanceof Error
        ? err.message
        : 'Failed to delete API key';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, authenticatedApi]);

  return { deleteApiKey, loading, error, clearError: () => setError(null) };
}