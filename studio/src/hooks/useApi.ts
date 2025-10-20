import { useState, useEffect, useCallback } from 'react';
import { api, ApiError } from '../utils/api';
import type { Template } from '../types';

export function usePrompts() {
  const [prompts, setPrompts] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPrompts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getPrompts();
      setPrompts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch prompts');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrompts();
  }, [fetchPrompts]);

  return { prompts, loading, error, refetch: fetchPrompts };
}

export function usePrompt(id: string | null) {
  const [prompt, setPrompt] = useState<Template | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPrompt = useCallback(async (promptId: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getPrompt(promptId);
      setPrompt(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch prompt');
      setPrompt(null);
    } finally {
      setLoading(false);
    }
  }, []);

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

export function useRender() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const render = useCallback(async (promptId: string, inputs: Record<string, unknown>) => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.renderPrompt(promptId, { inputs });
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
  }, []);

  return { render, loading, error, clearError: () => setError(null) };
}

export function useCreatePrompt() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createPrompt = useCallback(async (template: Omit<Template, 'inputs'> & {
    inputs: Record<string, { type: string; required: boolean; default?: unknown }>
  }) => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.createPrompt(template);
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
  }, []);

  return { createPrompt, loading, error, clearError: () => setError(null) };
}

export function useUpdatePrompt() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updatePrompt = useCallback(async (id: string, template: Partial<Omit<Template, 'id' | 'inputs'>> & {
    inputs?: Record<string, { type: string; required: boolean; default?: unknown }>
  }) => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.updatePrompt(id, template);
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
  }, []);

  return { updatePrompt, loading, error, clearError: () => setError(null) };
}